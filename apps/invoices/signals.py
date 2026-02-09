# Invoice signals - DISABLED
# Ledger entry creation is now handled explicitly in views (InvoiceCreateView and InvoiceUpdateView)
# to avoid race condition where signal fires before invoice items are saved.

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from .models import Invoice

# The signal-based approach has been replaced with explicit ledger creation in views
# See InvoiceCreateView.form_valid() and InvoiceUpdateView.form_valid()
