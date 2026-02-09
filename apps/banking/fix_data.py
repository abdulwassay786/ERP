import os
import django
from django.db.models import Count

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_project.settings')
django.setup()

from apps.banking.models import BankAccount

def fix_duplicates():
    print("Checking for duplicates...")
    duplicates = BankAccount.objects.values('account_number').annotate(count=Count('id')).filter(count__gt=1)
    
    if not duplicates:
        print("No duplicates found.")
        return

    for dup in duplicates:
        print(f"Found {dup['count']} accounts with number '{dup['account_number']}'")
        accounts = list(BankAccount.objects.filter(account_number=dup['account_number']).order_by('created_at'))
        
        # Keep the first one, rename the users
        for i, acc in enumerate(accounts[1:], 1):
            new_number = f"{acc.account_number}-DUP-{i}"
            print(f"Renaming account {acc.id} to {new_number}")
            acc.account_number = new_number
            acc.save()

if __name__ == '__main__':
    fix_duplicates()
