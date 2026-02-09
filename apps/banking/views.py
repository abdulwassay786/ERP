from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse
from django.views import View
from .models import BankAccount, BankTransaction
from .forms import BankAccountForm, BankTransactionForm
from apps.core.pdf_utils import PDFGenerator
from io import BytesIO
from datetime import datetime


class BankAccountListView(LoginRequiredMixin, ListView):
    """List all bank accounts for the user's company"""
    model = BankAccount
    template_name = 'banking/bankaccount_list.html'
    context_object_name = 'accounts'
    paginate_by = 20

    def get_queryset(self):
        """Filter bank accounts by user's company"""
        if self.request.user.company:
            return BankAccount.objects.filter(company=self.request.user.company, is_deleted=False)
        return BankAccount.objects.none()


class BankAccountCreateView(LoginRequiredMixin, CreateView):
    """Create a new bank account"""
    model = BankAccount
    form_class = BankAccountForm
    template_name = 'banking/bankaccount_form.html'
    success_url = reverse_lazy('banking:account_list')

    def form_valid(self, form):
        form.instance.company = self.request.user.company
        self.object = form.save()

        if self.request.headers.get("HX-Request"):
            from django.http import HttpResponse
            response = HttpResponse(status=204)
            response['HX-Location'] = self.get_success_url()
            return response

        messages.success(self.request, "Bank account created successfully.")
        return super().form_valid(form)

class BankAccountUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing bank account"""
    model = BankAccount
    form_class = BankAccountForm
    template_name = 'banking/bankaccount_form.html'
    success_url = reverse_lazy('banking:account_list')

    def get_queryset(self):
        """Only allow editing bank accounts from user's company"""
        if self.request.user.company:
            return BankAccount.objects.filter(company=self.request.user.company, is_deleted=False)
        return BankAccount.objects.none()

    def form_valid(self, form):
        messages.success(self.request, 'Bank account updated successfully.')
        return super().form_valid(form)


class BankAccountDeleteView(LoginRequiredMixin, DeleteView):
    model = BankAccount
    success_url = reverse_lazy('banking:account_list')

    def get_queryset(self):
        return BankAccount.objects.filter(
            company=self.request.user.company,
            is_deleted=False
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.soft_delete()

        if request.headers.get("HX-Request"):
            from django.http import HttpResponse
            return HttpResponse("")

        messages.success(request, "Bank account deleted successfully.")
        return redirect(self.success_url)



class BankTransactionListView(LoginRequiredMixin, ListView):
    """List all bank transactions for the user's company"""
    model = BankTransaction
    template_name = 'banking/banktransaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        """Filter transactions by user's company, optionally by account"""
        if not self.request.user.company:
            return BankTransaction.objects.none()
        
        queryset = BankTransaction.objects.filter(
            company=self.request.user.company,
            is_deleted=False
        )
        
        account_id = self.request.GET.get('account')
        if account_id:
            queryset = queryset.filter(bank_account_id=account_id)
        
        return queryset

    def get_context_data(self, **kwargs):
        """Add bank accounts to context"""
        context = super().get_context_data(**kwargs)
        if self.request.user.company:
            context['accounts'] = BankAccount.objects.filter(
                company=self.request.user.company,
                is_deleted=False
            )
        else:
            context['accounts'] = BankAccount.objects.none()
        return context


class BankTransactionCreateView(LoginRequiredMixin, CreateView):
    """Create a new bank transaction"""
    model = BankTransaction
    form_class = BankTransactionForm
    template_name = 'banking/banktransaction_form.html'
    success_url = reverse_lazy('banking:transaction_list')

    def get_form_kwargs(self):
        """Pass company to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.request.user.company
        return kwargs

    def form_valid(self, form):
        """Set the company before saving"""
        form.instance.company = self.request.user.company
        messages.success(self.request, 'Transaction created successfully.')
        return super().form_valid(form)


class BankTransactionDeleteView(LoginRequiredMixin, DeleteView):
    """Soft delete a bank transaction"""
    model = BankTransaction
    success_url = reverse_lazy('banking:transaction_list')

    def get_queryset(self):
        """Only allow deleting transactions from user's company"""
        if self.request.user.company:
            return BankTransaction.objects.filter(company=self.request.user.company, is_deleted=False)
        return BankTransaction.objects.none()

    def delete(self, request, *args, **kwargs):
        """Soft delete instead of hard delete"""
        self.object = self.get_object()
        self.object.soft_delete()
        messages.success(request, 'Transaction deleted successfully.')
        return redirect(self.success_url)

    def get(self, request, *args, **kwargs):
        """Handle GET requests by performing delete"""
        return self.delete(request, *args, **kwargs)


class TransactionListPDFView(LoginRequiredMixin, View):
    """Export bank transactions to PDF"""
    
    def get(self, request, *args, **kwargs):
        # Get filtered transactions
        if not request.user.company:
            return HttpResponse("No company associated", status=400)
            
        queryset = BankTransaction.objects.filter(
            company=request.user.company,
            is_deleted=False
        ).select_related('bank_account')
        
        # Apply account filter if provided
        account_id = request.GET.get('account')
        selected_account = None
        if account_id:
            queryset = queryset.filter(bank_account_id=account_id)
            try:
                selected_account = BankAccount.objects.get(
                    id=account_id,
                    company=request.user.company
                )
            except BankAccount.DoesNotExist:
                pass
        
        # Order by date
        queryset = queryset.order_by('-transaction_date', '-id')
        
        # Create PDF
        buffer = BytesIO()
        title = "Bank Transactions Report"
        if selected_account:
            title = f"Transactions - {selected_account.account_name}"
            
        pdf = PDFGenerator(buffer, title=title, company=request.user.company)
        pdf.add_company_header()
        
        # Add account info if filtered
        if selected_account:
            pdf.add_spacer(0.2)
            account_info = {
                "Account Name": selected_account.account_name,
                "Account Number": selected_account.account_number,
                "Bank": selected_account.bank_name,
                "Current Balance": f"Rs {selected_account.balance:,.2f}"
            }
            pdf.add_summary_section("Account Details", account_info)
        
        pdf.add_spacer(0.3)
        
        # Build transaction table (Note: BankTransaction model uses 'credit'/'debit', not 'deposit'/'withdrawal')
        table_data = [['Date', 'Description', 'Type', 'Amount']]
        
        total_credits = 0
        total_debits = 0
        
        for txn in queryset:
            amount_str = f"Rs {txn.amount:,.2f}"
            if txn.transaction_type == 'debit':
                amount_str = f"-{amount_str}"
                total_debits += txn.amount
            else:  # credit
                amount_str = f"+{amount_str}"
                total_credits += txn.amount
                
            table_data.append([
                txn.transaction_date.strftime('%Y-%m-%d'),
                txn.description[:50] + '...' if len(txn.description) > 50 else txn.description,
                txn.transaction_type.title(),
                amount_str
            ])
        
        if len(table_data) > 1:
            from reportlab.lib.units import inch
            table = pdf.create_table(
                table_data,
                col_widths=[1.2*inch, 3*inch, 1*inch, 1.3*inch]
            )
            pdf.elements.append(table)
        else:
            from reportlab.platypus import Paragraph
            no_data = Paragraph("No transactions found.", pdf.styles['Normal'])
            pdf.elements.append(no_data)
        
        # Add summary
        if len(table_data) > 1:
            summary = {
                "Total Transactions": str(len(table_data) - 1),
                "Total Credits": f"Rs {total_credits:,.2f}",
                "Total Debits": f"Rs {total_debits:,.2f}",
                "Net Change": f"Rs {(total_credits - total_debits):,.2f}"
            }
            pdf.add_summary_section("Summary", summary)
        
        # Build PDF
        pdf.build()
        
        # Return response
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
