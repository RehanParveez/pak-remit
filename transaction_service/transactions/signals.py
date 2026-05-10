from django.dispatch import receiver
from django.dispatch import receiver
from django.db.models.signals import post_save
from transactions.models import Transaction
from transactions.tasks import process_transaction_async

@receiver(post_save, sender=Transaction)
def handle_transaction_saved(sender, instance, created, **kwargs):
    # Requirement: Only trigger the background worker when a NEW txn is 'initiated'
    if created and instance.status == 'initiated':
        process_transaction_async.delay(instance.id)