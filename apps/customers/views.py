from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q
from .models import Customer
from .forms import CustomerForm


class CustomerListView(LoginRequiredMixin, ListView):
    """List all customers for the user's company"""
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        """Filter customers by user's company"""
        if self.request.user.company:
            return Customer.objects.filter(company=self.request.user.company, is_deleted=False)
        return Customer.objects.none()


class CustomerDetailView(LoginRequiredMixin, DetailView):
    """View customer details with purchase history"""
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'

    def get_queryset(self):
        """Only allow viewing customers from user's company"""
        if self.request.user.company:
            return Customer.objects.filter(company=self.request.user.company, is_deleted=False)
        return Customer.objects.none()

    def get_context_data(self, **kwargs):
        """Add invoice history and financial summary"""
        context = super().get_context_data(**kwargs)
        customer = self.object
        
        # Get all invoices for this customer
        from apps.invoices.models import Invoice
        invoices = Invoice.objects.filter(
            customer=customer,
            company=self.request.user.company,
            is_deleted=False
        ).order_by('-date')
        
        # Calculate financial summary
        total_purchases = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
        paid_invoices = invoices.filter(status='paid')
        total_paid = paid_invoices.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Pending amount (invoices that are not paid or cancelled)
        pending_invoices = invoices.filter(Q(status='draft') | Q(status='sent'))
        pending_amount = pending_invoices.aggregate(total=Sum('total_amount'))['total'] or 0
        
        context['invoices'] = invoices
        context['total_purchases'] = total_purchases
        context['total_paid'] = total_paid
        context['pending_amount'] = pending_amount
        context['invoice_count'] = invoices.count()
        
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    """Create a new customer"""
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def get_form_kwargs(self):
        """Pass company to form"""
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs

    def form_valid(self, form):
        """Set the company before saving"""
        form.instance.company = self.request.user.company
        response = super().form_valid(form)
        
        # If this is an HTMX request from invoice form, return script to update dropdown
        if self.request.headers.get('HX-Request'):
            from django.http import HttpResponse
            customer = self.object
            return HttpResponse(
                f"""
                <script>
                    // Add new customer to dropdown
                    const customerSelect = document.getElementById('id_customer');
                    const newOption = new Option('{customer.name}', '{customer.id}', true, true);
                    customerSelect.add(newOption);
                    
                    // Close modal
                    document.getElementById('customer-creation-modal').style.display = 'none';
                    
                    // Show success message
                    alert('Customer created successfully!');
                </script>
                """,
                content_type='text/html'
            )
        
        messages.success(self.request, 'Customer created successfully.')
        return response



class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing customer"""
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')

    def get_queryset(self):
        """Only allow editing customers from user's company"""
        if self.request.user.company:
            return Customer.objects.filter(company=self.request.user.company, is_deleted=False)
        return Customer.objects.none()

    def form_valid(self, form):
        messages.success(self.request, 'Customer updated successfully.')
        return super().form_valid(form)


class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    """Soft delete a customer"""
    model = Customer
    template_name = 'customers/customer_confirm_delete.html'
    success_url = reverse_lazy('customers:list')

    def get_queryset(self):
        """Only allow deleting customers from user's company"""
        if self.request.user.company:
            return Customer.objects.filter(company=self.request.user.company, is_deleted=False)
        return Customer.objects.none()

    def delete(self, request, *args, **kwargs):
        """Soft delete instead of hard delete"""
        self.object = self.get_object()
        self.object.soft_delete()
        messages.success(request, 'Customer deleted successfully.')
        return redirect(self.success_url)
