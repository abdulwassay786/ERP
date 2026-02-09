from django.core.management.base import BaseCommand
from apps.core.models import Company
from apps.ledger.services import LedgerService
from apps.ledger.models import LedgerEntry
from decimal import Decimal


class Command(BaseCommand):
    help = 'Audit ledger balances and recalculate if needed'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Audit specific company only'
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix corrupted balances'
        )
    
    def handle(self, *args, **options):
        companies = Company.objects.all()
        
        if options['company_id']:
            companies = companies.filter(id=options['company_id'])
        
        total_errors = 0
        
        for company in companies:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Auditing: {company.name}")
            self.stdout.write(f"{'='*60}")
            
            # Check customers
            customer_errors = self._audit_party(company, 'customer', options['fix'])
            
            # Check suppliers
            supplier_errors = self._audit_party(company, 'supplier', options['fix'])
            
            total_errors += customer_errors + supplier_errors
        
        self.stdout.write(f"\n{'='*60}")
        if total_errors == 0:
            self.stdout.write(self.style.SUCCESS(f"✓ Audit complete. No errors found."))
        else:
            if options['fix']:
                self.stdout.write(self.style.SUCCESS(f"✓ Audit complete. Fixed {total_errors} errors."))
            else:
                self.stdout.write(self.style.WARNING(f"⚠ Audit complete. Found {total_errors} errors. Run with --fix to correct them."))
    
    def _audit_party(self, company, party_type, fix_errors):
        """Audit all parties of a given type"""
        errors = 0
        
        # Get all unique party IDs
        party_ids = LedgerEntry.objects.filter(
            company=company,
            party_type=party_type
        ).values_list('party_id', flat=True).distinct()
        
        for party_id in party_ids:
            # Calculate expected balance
            entries = LedgerEntry.objects.filter(
                company=company,
                party_type=party_type,
                party_id=party_id
            ).order_by('transaction_date', 'created_at')
            
            expected_balance = Decimal('0.00')
            has_error = False
            
            for entry in entries:
                expected_balance += entry.debit - entry.credit
                
                if entry.running_balance != expected_balance:
                    if not has_error:
                        self.stdout.write(
                            self.style.ERROR(f"  ✗ {party_type.title()} {party_id}: Balance mismatch")
                        )
                        has_error = True
                        errors += 1
            
            if has_error and fix_errors:
                # Recalculate
                LedgerService.recalculate_party_balance(company, party_type, party_id)
                self.stdout.write(
                    self.style.SUCCESS(f"    → Fixed {party_type} {party_id}")
                )
        
        if errors == 0:
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ All {party_type}s OK")
            )
        
        return errors
