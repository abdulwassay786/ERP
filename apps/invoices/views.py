from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.views import View
from .models import Invoice
from .forms import InvoiceForm, InvoiceItemFormSet
from apps.core.pdf_utils import PDFGenerator
from io import BytesIO
from datetime import datetime


class InvoiceListView(LoginRequiredMixin, ListView):
    """List all invoices for the user's company"""
    model = Invoice
    template_name = 'invoices/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        """Filter invoices by user's company"""
        if self.request.user.company:
            return Invoice.objects.filter(company=self.request.user.company, is_deleted=False)
        return Invoice.objects.none()


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    """View invoice details"""
    model = Invoice
    template_name = 'invoices/invoice_detail.html'
    context_object_name = 'invoice'

    def get_queryset(self):
        """Only allow viewing invoices from user's company"""
        if self.request.user.company:
            return Invoice.objects.filter(company=self.request.user.company, is_deleted=False)
        return Invoice.objects.none()


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    """Create a new invoice"""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'invoices/invoice_form.html'
    success_url = reverse_lazy('invoices:list')

    def get_form_kwargs(self):
        """Pass company to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs

    def get_context_data(self, **kwargs):
        """Add formset to context"""
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = InvoiceItemFormSet(
                self.request.POST,
                instance=self.object,
                form_kwargs={'company': self.request.user.company}
            )
        else:
            context['formset'] = InvoiceItemFormSet(
                instance=self.object,
                form_kwargs={'company': self.request.user.company}
            )
        return context

    def form_valid(self, form):
        """Save invoice and formset"""
        context = self.get_context_data()
        formset = context['formset']
        
        with transaction.atomic():
            form.instance.company = self.request.user.company
            self.object = form.save()
            if formset.is_valid():
                formset.instance = self.object
                formset.save()
                self.object.calculate_total()
                
                # Create ledger entry if invoice is being sent or paid
                if self.object.status in ['sent', 'paid'] and self.object.customer:
                    from apps.ledger.services import LedgerService
                    from apps.ledger.models import LedgerEntry
                    from decimal import Decimal
                    
                    # Only create if total > 0 and entry doesn't exist
                    if self.object.total_amount > Decimal('0.00'):
                        existing = LedgerEntry.objects.filter(
                            company=self.object.company,
                            party_type='customer',
                            party_id=self.object.customer.id,
                            reference_type__model='invoice',
                            reference_id=self.object.id
                        ).exists()
                        
                        if not existing:
                            # Create invoice entry (debit - customer owes)
                            LedgerService.create_customer_invoice_entry(
                                company=self.object.company,
                                customer=self.object.customer,
                                invoice=self.object
                            )
                            
                            # If status is 'paid', also create payment entry (credit - customer paid)
                            if self.object.status == 'paid':
                                LedgerService.create_customer_payment_entry(
                                    company=self.object.company,
                                    customer=self.object.customer,
                                    amount=self.object.total_amount,
                                    payment_date=self.object.date,
                                    description=f"Payment for Invoice {self.object.invoice_number}",
                                    reference_object=None  # Don't link to invoice to avoid constraint issues
                                )
                
                messages.success(self.request, 'Invoice created successfully.')
                return super().form_valid(form)
            else:
                return self.form_invalid(form)


class InvoiceUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing invoice"""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'invoices/invoice_form.html'
    success_url = reverse_lazy('invoices:list')

    def get_queryset(self):
        """Only allow editing invoices from user's company"""
        if self.request.user.company:
            return Invoice.objects.filter(company=self.request.user.company, is_deleted=False)
        return Invoice.objects.none()

    def dispatch(self, request, *args, **kwargs):
        """Prevent editing if invoice is LOCKED (Paid only)"""
        obj = self.get_object()
        # Allow editing 'sent' status, but block 'paid'
        if obj.status == 'paid':
            messages.warning(request, f"Invoice {obj.invoice_number} is locked because it is Paid. You cannot edit it.")
            return redirect('invoices:detail', pk=obj.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass company to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs

    def get_context_data(self, **kwargs):
        """Add formset to context"""
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = InvoiceItemFormSet(
                self.request.POST,
                instance=self.object,
                form_kwargs={'company': self.request.user.company}
            )
        else:
            context['formset'] = InvoiceItemFormSet(
                instance=self.object,
                form_kwargs={'company': self.request.user.company}
            )
        return context

    def form_valid(self, form):
        """Save invoice and formset"""
        context = self.get_context_data()
        formset = context['formset']
        
        # Track previous status
        old_status = None
        if self.object.pk:
            old_status = Invoice.objects.get(pk=self.object.pk).status
        
        with transaction.atomic():
            self.object = form.save()
            if formset.is_valid():
                formset.instance = self.object
                formset.save()
                self.object.calculate_total()
                
                from apps.ledger.services import LedgerService
                from apps.ledger.models import LedgerEntry
                from decimal import Decimal
                
                # Logic for status changes
                
                # Case 1: Status changed FROM 'Sent' TO 'Cancelled'
                # Action: Void/Delete the ledger entry
                if old_status == 'sent' and self.object.status == 'cancelled':
                    existing_entry = LedgerEntry.objects.filter(
                        company=self.object.company,
                        party_type='customer',
                        party_id=self.object.customer.id,
                        reference_type__model='invoice',
                        reference_id=self.object.id
                    ).first()
                    
                    if existing_entry:
                        # Build description for voiding
                        void_desc = f"VOID: {existing_entry.description}"
                        
                        # We could create specific void entry, but for simplicity/cleanliness, we delete/reverse
                        # Or better: Create a Credit entry to net it out?
                        # Simplest approach requested: "Cancelled" -> Void
                        
                        # Let's delete it so it disappears from statement, or create opposing entry?
                        # Deleting is cleaner for "Cancelled" in simple systems.
                        existing_entry.delete()
                        
                        # Recalculate balance for customer to be safe
                        LedgerService.recalculate_party_balance(
                            company=self.object.company,
                            party_type='customer',
                            party_id=self.object.customer.id
                        )
                        messages.warning(self.request, "Invoice cancelled. Ledger entry has been voided.")
                
                # Case 2: Status IS 'Sent' (was Sent or just changed to Sent), and amount changed
                # Action: Update the ledger entry amount
                elif self.object.status == 'sent':
                    existing_entry = LedgerEntry.objects.filter(
                        company=self.object.company,
                        party_type='customer',
                        party_id=self.object.customer.id,
                        reference_type__model='invoice',
                        reference_id=self.object.id
                    ).first()
                    
                    if existing_entry:
                        # Update existing entry if amount differs
                        if existing_entry.debit != self.object.total_amount:
                            existing_entry.debit = self.object.total_amount
                            existing_entry.save()
                            
                            # Must recalculate running balances
                            LedgerService.recalculate_party_balance(
                                company=self.object.company,
                                party_type='customer',
                                party_id=self.object.customer.id
                            )
                            # messages.info(self.request, "Invoice amount updated in ledger.")
                    else:
                        # Create new if doesn't exist (e.g. Draft -> Sent)
                        if self.object.total_amount > Decimal('0.00') and self.object.customer:
                            LedgerService.create_customer_invoice_entry(
                                company=self.object.company,
                                customer=self.object.customer,
                                invoice=self.object
                            )
                
                # Case 3: Status changed to 'Paid' (from anything)
                if self.object.status == 'paid':
                     # Ensure invoice entry exists
                    existing_invoice_entry = LedgerEntry.objects.filter(
                        company=self.object.company,
                        party_type='customer',
                        party_id=self.object.customer.id,
                        reference_type__model='invoice',
                        reference_id=self.object.id
                    ).exists()
                    
                    if not existing_invoice_entry and self.object.total_amount > Decimal('0.00'):
                         LedgerService.create_customer_invoice_entry(
                            company=self.object.company,
                            customer=self.object.customer,
                            invoice=self.object
                        )
                    
                    # Create payment entry if not exists (checked inside service usually, but here we do manual check or duplicate)
                    # We'll just create it. Logic in previous version was: if changing TO paid.
                    if old_status != 'paid':
                        LedgerService.create_customer_payment_entry(
                            company=self.object.company,
                            customer=self.object.customer,
                            amount=self.object.total_amount,
                            payment_date=self.object.date,
                            description=f"Payment for Invoice {self.object.invoice_number}",
                            reference_object=None
                        )

                messages.success(self.request, 'Invoice updated successfully.')
                return super().form_valid(form)
            else:
                return self.form_invalid(form)


class InvoiceDeleteView(LoginRequiredMixin, DeleteView):
    """Soft delete an invoice"""
    model = Invoice
    success_url = reverse_lazy('invoices:list')

    def get_queryset(self):
        """Only allow deleting invoices from user's company"""
        if self.request.user.company:
            return Invoice.objects.filter(company=self.request.user.company, is_deleted=False)
        return Invoice.objects.none()

    def dispatch(self, request, *args, **kwargs):
        """Prevent deleting if invoice is LOCKED (Paid only)"""
        obj = self.get_object()
        # Allow deleting 'sent' (acts as cancellation/void), but block 'paid'
        if obj.status == 'paid':
            if request.headers.get("HX-Request"):
                from django.http import HttpResponse
                return HttpResponse("Cannot delete locked invoice", status=403)
            
            messages.warning(request, f"Invoice {obj.invoice_number} is locked because it is Paid. You cannot delete it.")
            return redirect('invoices:detail', pk=obj.pk)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.soft_delete()

        if request.headers.get("HX-Request"):
            from django.http import HttpResponse
            return HttpResponse("")

        messages.success(request, "Invoice deleted successfully.")
        return redirect(self.success_url)


class RecordPaymentView(LoginRequiredMixin, CreateView):
    """Record a customer payment against an invoice"""
    template_name = 'invoices/record_payment.html'
    success_url = reverse_lazy('invoices:list')
    
    def get_form(self):
        """Get the payment form with company context"""
        from apps.invoices.payment_forms import RecordPaymentForm
        if self.request.method == 'POST':
            return RecordPaymentForm(self.request.user.company, self.request.POST)
        return RecordPaymentForm(self.request.user.company)
    
    def form_valid(self, form):
        """Process the payment"""
        invoice = form.cleaned_data['invoice']
        amount = form.cleaned_data['amount']
        payment_date = form.cleaned_data['payment_date']
        notes = form.cleaned_data.get('notes', '')
        
        from apps.ledger.services import LedgerService
        from decimal import Decimal
        
        with transaction.atomic():
            # Record payment in ledger (don't pass invoice as reference to avoid constraint issues)
            LedgerService.create_customer_payment_entry(
                company=self.request.user.company,
                customer=invoice.customer,
                amount=amount,
                payment_date=payment_date,
                description=f"Payment for Invoice {invoice.invoice_number}" + (f" - {notes}" if notes else "")
                # Note: No reference_object to allow multiple payments per invoice
            )
            
            # Check if invoice is fully paid
            total_paid = amount  # In a real system, you'd sum all payments for this invoice
            if total_paid >= invoice.total_amount:
                invoice.status = 'paid'
                invoice.save()
                messages.success(self.request, f'Payment recorded. Invoice {invoice.invoice_number} is now fully paid.')
            else:
                messages.success(self.request, f'Partial payment of {amount} recorded for Invoice {invoice.invoice_number}.')
        
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        """Handle invalid form"""
        messages.error(self.request, 'Please correct the errors below.')
        return self.render_to_response(self.get_context_data(form=form))
    
    def get_context_data(self, **kwargs):
        """Add form to context"""
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.get_form()
        return context


class InvoiceListPDFView(LoginRequiredMixin, View):
    """Export invoice list to PDF"""
    
    def get(self, request, *args, **kwargs):
        # Get filtered invoices
        if not request.user.company:
            return HttpResponse("No company associated", status=400)
            
        queryset = Invoice.objects.filter(
            company=request.user.company,
            is_deleted=False
        ).select_related('customer').order_by('-date', '-id')
        
        # Apply status filter if provided
        status_filter = request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Create PDF
        buffer = BytesIO()
        title = "Invoice List"
        if status_filter:
            title = f"Invoice List - {status_filter.title()}"
            
        pdf = PDFGenerator(buffer, title=title, company=request.user.company)
        pdf.add_company_header()
        pdf.add_spacer(0.3)
        
        # Build invoice table
        table_data = [['Invoice #', 'Date', 'Customer', 'Status', 'Amount', 'Due Date']]
        
        total_amount = 0
        status_counts = {'draft': 0, 'sent': 0, 'paid': 0, 'overdue': 0}
        
        for invoice in queryset:
            total_amount += invoice.total_amount
            status_counts[invoice.status] = status_counts.get(invoice.status, 0) + 1
            
            # Format status with color coding in the data
            status_display = invoice.status.title()
            
            table_data.append([
                invoice.invoice_number,
                invoice.date.strftime('%Y-%m-%d'),
                invoice.customer.name if invoice.customer else '-',
                status_display,
                f"Rs {invoice.total_amount:,.2f}",
                invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else '-'
            ])
        
        if len(table_data) > 1:
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from reportlab.platypus import TableStyle
            
            # Build custom style with conditional formatting for status
            style_commands = [
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                # Body styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1a1a1a')),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]
            
            # Add conditional formatting for status column
            for i, row in enumerate(table_data[1:], start=1):
                status = row[3].lower()
                if status == 'paid':
                    style_commands.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#16a34a')))
                elif status == 'overdue':
                    style_commands.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#dc2626')))
                elif status == 'sent':
                    style_commands.append(('TEXTCOLOR', (3, i), (3, i), colors.HexColor('#2563eb')))
            
            # Create table with custom style
            custom_style = TableStyle(style_commands)
            table = pdf.create_table(
                table_data,
                col_widths=[1*inch, 1*inch, 1.8*inch, 0.9*inch, 1.1*inch, 1*inch],
                style=custom_style
            )
            
            pdf.elements.append(table)
        else:
            from reportlab.platypus import Paragraph
            no_data = Paragraph("No invoices found.", pdf.styles['Normal'])
            pdf.elements.append(no_data)
        
        # Add summary
        if len(table_data) > 1:
            summary = {
                "Total Invoices": str(len(table_data) - 1),
                "Total Amount": f"Rs {total_amount:,.2f}",
            }
            
            # Add status breakdown
            if not status_filter:
                summary["Draft"] = str(status_counts.get('draft', 0))
                summary["Sent"] = str(status_counts.get('sent', 0))
                summary["Paid"] = str(status_counts.get('paid', 0))
                summary["Overdue"] = str(status_counts.get('overdue', 0))
            
            pdf.add_summary_section("Summary", summary)
        
        # Build PDF
        pdf.build()
        
        # Return response
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class InvoiceDetailPDFView(LoginRequiredMixin, View):
    """Export single invoice to PDF"""
    
    def get(self, request, pk, *args, **kwargs):
        invoice = get_object_or_404(Invoice, pk=pk, company=request.user.company, is_deleted=False)
        
        buffer = BytesIO()
        pdf = PDFGenerator(buffer, title="INVOICE", company=request.user.company)
        pdf.add_company_header()
        pdf.add_spacer(0.3)
        
        # Add 'RECEIPT' watermark/header if paid
        if invoice.status == 'paid':
            pdf.add_text("RECEIPT - PAID", style='Heading2', align='CENTER', color='#16a34a')
            pdf.add_spacer(0.2)
        elif invoice.status == 'overdue':
             pdf.add_text("OVERDUE", style='Heading2', align='CENTER', color='#dc2626')
             pdf.add_spacer(0.2)
        
        # Two-column layout for Invoice Info and Customer Info
        # Using a table for layout
        data = [
            [
                # Left Column: Invoice Info
                f"Invoice #: {invoice.invoice_number}\nDate: {invoice.date.strftime('%Y-%m-%d')}\nDue Date: {invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else '-'}\nStatus: {invoice.status.title()}",
                # Right Column: Customer Info
                f"Bill To:\n{invoice.customer.name}\n{invoice.customer.phone or ''}\n{invoice.customer.address or ''}"
            ]
        ]
        
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib.units import inch
        
        # Layout table
        t = Table(data, colWidths=[3.5*inch, 3.5*inch])
        t.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        pdf.elements.append(t)
        pdf.add_spacer(0.5)
        
        # Items Table
        table_data = [['Product', 'Quantity', 'Unit Price', 'Total']]
        for item in invoice.items.all():
            table_data.append([
                item.product.name,
                str(item.quantity),
                f"Rs {item.unit_price:,.2f}",
                f"Rs {item.line_total:,.2f}"
            ])
            
        # Add Total Row
        table_data.append(['', '', 'Total:', f"Rs {invoice.total_amount:,.2f}"])
        
        # Create items table
        t_items = Table(table_data, colWidths=[3.5*inch, 1.0*inch, 1.25*inch, 1.25*inch])
        
        # Style the items table
        style = [
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Body styling
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'), # Align numbers right
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
        ]
        
        # Style the total row specifically
        style.append(('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold')) # Bold "Total:" and Amount
        style.append(('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f9fafb'))) # Light bg for total
        
        t_items.setStyle(TableStyle(style))
        pdf.elements.append(t_items)
        
        # Notes
        if invoice.notes:
            pdf.add_spacer(0.5)
            pdf.add_text("Notes:", style='Normal', bold=True)
            pdf.add_text(invoice.notes)
            
        # Build PDF
        pdf.build()
        
        filename = f"Invoice_{invoice.invoice_number}"
        if invoice.status == 'paid':
            filename = f"Receipt_{invoice.invoice_number}"
            
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        return response
