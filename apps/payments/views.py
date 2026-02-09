from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import render
from django.db import transaction, models
from django.contrib import messages
from decimal import Decimal

from apps.core.models import Company
from apps.invoices.models import Invoice
from apps.ledger.services import LedgerService
from .models import Payment, PaymentAllocation
from .forms import PaymentForm


class PaymentListView(LoginRequiredMixin, ListView):
    """List all payments for the company"""
    model = Payment
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_queryset(self):
        return Payment.objects.filter(
            company=self.request.user.company, 
            is_deleted=False
        ).select_related('customer')


class PaymentCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new payment and allocate to invoices.
    CRITICAL: Handles allocation logic and Ledger updates atomically.
    """
    model = Payment
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'
    success_url = reverse_lazy('payments:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs

    def form_valid(self, form):
        context = self.get_context_data()
        
        # 1. Save the Payment first
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.company = self.request.user.company
            self.object.save()
            
            # 2. Handle Allocations
            # Check for manual allocations from POST data
            allocations_made = False
            total_allocated = Decimal('0.00')

            # [NEW] Check if a specific invoice was selected in the form
            selected_invoice = form.cleaned_data.get('invoice')
            if selected_invoice:
                 # Check how much is outstanding on this invoice
                 paid = selected_invoice.payment_allocations.aggregate(
                     total=models.Sum('amount')
                 )['total'] or Decimal('0.00')
                 
                 outstanding = selected_invoice.total_amount - paid
                 
                 if outstanding > 0:
                     # Allocate as much as possible to this invoice
                     to_allocate = min(self.object.amount, outstanding)
                     
                     PaymentAllocation.objects.create(
                         payment=self.object,
                         invoice=selected_invoice,
                         amount=to_allocate
                     )
                     total_allocated += to_allocate
                     allocations_made = True
            
            # Process manual inputs: name="allocation_{invoice_id}" (Overrides/Adds to selection)
            for key, value in self.request.POST.items():
                if key.startswith('allocation_') and value:
                    try:
                        invoice_id = int(key.split('_')[1])
                        # specific invoice logic handles duplicates if user selected invoice AND typed in manual field
                        # for now, let's assume manual inputs are additive or distinct. 
                        # If user selected invoice A and typed allocation for A, we might double allocate if we are not careful.
                        # Constraint unique_payment_invoice_allocation prevents duplicate rows, so create() will fail if we try again.
                        
                        # To be safe, check if we already allocated to this invoice (from selected_invoice step)
                        if selected_invoice and invoice_id == selected_invoice.id:
                            continue 
                            
                        amount = Decimal(value)
                        if amount > 0:
                            invoice = Invoice.objects.get(
                                id=invoice_id, 
                                company=self.request.user.company,
                                customer=self.object.customer
                            )
                            PaymentAllocation.objects.create(
                                payment=self.object,
                                invoice=invoice,
                                amount=amount
                            )
                            total_allocated += amount
                            allocations_made = True
                    except (ValueError, Invoice.DoesNotExist):
                        continue

            # 3. FIFO Auto-Allocation (if no manual allocations or selection)
            # Default behavior: If users didn't customize, auto-allocate to oldest unpaid
            if not allocations_made:
                unpaid_invoices = Invoice.objects.filter(
                    company=self.object.company,
                    customer=self.object.customer,
                    status__in=['sent', 'partial'] # logic will need update after status refactor
                ).order_by('date') # Oldest first
                
                remaining_payment = self.object.amount
                
                for invoice in unpaid_invoices:
                    if remaining_payment <= 0:
                        break
                        
                    # Calculate how much is still owed on this invoice
                    # (Refactor note: Using current naive logic, will need to be robust)
                    already_paid = invoice.payment_allocations.aggregate(
                        total=models.Sum('amount')
                    )['total'] or Decimal('0.00')
                    
                    outstanding = invoice.total_amount - already_paid
                    
                    if outstanding <= 0:
                        continue
                        
                    to_allocate = min(remaining_payment, outstanding)
                    
                    PaymentAllocation.objects.create(
                        payment=self.object,
                        invoice=invoice,
                        amount=to_allocate
                    )
                    
                    remaining_payment -= to_allocate
                    total_allocated = self.object.amount - remaining_payment

            # 4. Create Ledger Entry
            # Credit Customer (Receivable)
            LedgerService.create_customer_payment_entry(
                company=self.object.company,
                customer=self.object.customer,
                amount=self.object.amount,
                payment_date=self.object.payment_date,
                description=f"Payment {self.object.payment_number} ({self.object.get_payment_method_display()})",
                reference_object=self.object
            )
            
            # 5. Update Invoice Statuses (Naive update for now, will improve)
            # Find all affected invoices and check if they are fully paid
            for allocation in self.object.allocations.all():
                invoice = allocation.invoice
                paid_total = invoice.payment_allocations.aggregate(
                    total=models.Sum('amount')
                )['total'] or Decimal('0.00')
                
                # Check status
                if paid_total >= invoice.total_amount:
                     # We can't set status directly if we refactor, but for now we set it 
                     # to maintain compatibility until Invoice model logic is updated
                     if invoice.status != 'paid':
                         invoice.status = 'paid'
                         invoice.save()
                
            messages.success(self.request, f"Payment of Rs {self.object.amount} recorded successfully.")
            return super().form_valid(form)


def unpaid_invoices_hx(request):
    """HTMX view to return unpaid invoices for a customer"""
    customer_id = request.GET.get('customer')
    if not customer_id:
        return render(request, 'payments/partials/unpaid_invoices.html', {'invoices': []})
        
    company = request.user.company
    
    # Get invoices that are NOT 'paid' and NOT 'cancelled'
    # Refactor Note: This relies on current status field. 
    # Logic should eventually check paid_amount < total_amount
    invoices = Invoice.objects.filter(
        company=company,
        customer_id=customer_id,
        is_deleted=False
    ).exclude(status__in=['paid', 'cancelled']).order_by('date')
    
    # Calculate outstanding for each
    invoice_list = []
    for inv in invoices:
        paid = inv.payment_allocations.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        outstanding = inv.total_amount - paid
        if outstanding > 0:
            inv.outstanding = outstanding # Annotate for template
            invoice_list.append(inv)
            
    return render(request, 'payments/partials/unpaid_invoices.html', {'invoices': invoice_list})
