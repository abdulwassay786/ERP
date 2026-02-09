from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.db import models
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import json


@login_required
def dashboard(request):
    """Dashboard view with comprehensive business metrics"""
    from apps.customers.models import Customer
    from apps.inventory.models import Product
    from apps.invoices.models import Invoice, InvoiceItem
    from apps.banking.models import BankAccount, BankTransaction
    
    context = {}
    if request.company:
        today = date.today()
        this_month_start = today.replace(day=1)
        
        # --- Inventory Metrics ---
        products = Product.objects.for_company(request.company)
        quantity_in_hand = products.aggregate(total=Sum('quantity_in_stock'))['total'] or 0
        
        # Calculate total inventory value
        inventory_value = products.aggregate(
            total=Sum(F('quantity_in_stock') * F('unit_price'), output_field=models.DecimalField())
        )['total'] or 0
        
        low_stock_items = products.filter(quantity_in_stock__lt=10).count()
        all_items_count = products.count()
        out_of_stock_items = products.filter(quantity_in_stock=0).count()
        active_items_count = products.filter(quantity_in_stock__gt=0).count()

        context.update({
            'quantity_in_hand': quantity_in_hand,
            'inventory_value': inventory_value,
            'low_stock_items': low_stock_items,
            'all_items_count': all_items_count,
            'out_of_stock_items': out_of_stock_items,
            'active_items_count': active_items_count,
        })

        # --- Financial Overview ---
        invoices = Invoice.objects.for_company(request.company)
        
        # Total Revenue (Paid invoices this month)
        total_revenue = invoices.filter(
            status='paid',
            date__gte=this_month_start
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Outstanding Amount (Sent + Overdue)
        outstanding_amount = invoices.filter(
            status__in=['sent', 'overdue']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Total Expenses (Bank transactions - withdrawals this month)
        total_expenses = BankTransaction.objects.filter(
            bank_account__company=request.company,
            transaction_type='withdrawal',
            transaction_date__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Net Profit
        net_profit = total_revenue - total_expenses
        
        # Ledger Metrics
        from apps.ledger.services import LedgerService
        
        receivables_list = LedgerService.get_all_outstanding_customers(request.company)
        total_receivables = sum(item['balance'] for item in receivables_list)
        
        payables_list = LedgerService.get_all_payable_suppliers(request.company)
        total_payables = sum(item['balance'] for item in payables_list)
        
        context.update({
            'total_revenue': total_revenue,
            'outstanding_amount': outstanding_amount,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'total_receivables': total_receivables,
            'total_payables': total_payables,
        })

        # --- Invoice Status ---
        draft_invoices_count = invoices.filter(status='draft').count()
        sent_invoices_count = invoices.filter(status='sent').count()
        overdue_invoices_count = invoices.filter(status='sent', due_date__lt=today).count()
        overdue_amount = invoices.filter(status='sent', due_date__lt=today).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        paid_this_month_count = invoices.filter(
            status='paid',
            date__gte=this_month_start
        ).count()
        
        context.update({
            'draft_invoices_count': draft_invoices_count,
            'sent_invoices_count': sent_invoices_count,
            'overdue_invoices_count': overdue_invoices_count,
            'overdue_amount': overdue_amount,
            'paid_this_month_count': paid_this_month_count,
        })

        # --- Top Selling Items ---
        top_selling = InvoiceItem.objects.filter(
            invoice__company=request.company,
            invoice__is_deleted=False,
            invoice__status='paid'  # Only count paid invoices
        ).values('product__name').annotate(
            total_qty=Sum('quantity'),
            total_rev=Sum('line_total')
        ).order_by('-total_qty')[:5]
        
        context['top_selling_items'] = top_selling

        # --- Bank Accounts ---
        bank_accounts = BankAccount.objects.for_company(request.company)
        total_bank_balance = bank_accounts.aggregate(total=Sum('balance'))['total'] or 0
        context['bank_accounts'] = bank_accounts
        context['total_bank_balance'] = total_bank_balance

        # --- Sales Trend (Last 6 Months) ---
        sales_trend = []
        sales_trend_labels = []
        sales_trend_data = []
        
        for i in range(5, -1, -1):  # 6 months, reversed for chronological order
            month_date = today - relativedelta(months=i)
            month_start = month_date.replace(day=1)
            if i == 0:
                month_end = today
            else:
                month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            revenue = invoices.filter(
                status='paid',
                date__range=[month_start, month_end]
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            sales_trend_labels.append(month_start.strftime('%b'))
            sales_trend_data.append(float(revenue))
        
        context['sales_trend_labels'] = json.dumps(sales_trend_labels)
        context['sales_trend_data'] = json.dumps(sales_trend_data)

        # --- Customer Insights ---
        customers = Customer.objects.for_company(request.company)
        total_customers = customers.count()
        
        # Active customers (with invoices this month)
        active_customers = customers.filter(
            invoices__date__gte=this_month_start
        ).distinct().count()
        
        # Top customer by revenue
        top_customer = customers.annotate(
            total_revenue=Sum('invoices__total_amount', filter=Q(invoices__status='paid'))
        ).order_by('-total_revenue').first()
        
        context.update({
            'total_customers': total_customers,
            'active_customers': active_customers,
            'top_customer': top_customer,
        })

        # --- Recent Activity ---
        recent_invoices = invoices.order_by('-created_at')[:5]
        recent_transactions = BankTransaction.objects.filter(
            bank_account__company=request.company
        ).order_by('-transaction_date')[:5]
        
        context['recent_invoices'] = recent_invoices
        context['recent_transactions'] = recent_transactions
    
    return render(request, 'core/dashboard.html', context)


class LoginView(auth_views.LoginView):
    """Custom login view"""
    template_name = 'core/login.html'
