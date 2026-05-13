from django.dispatch import receiver
from django.db.models.signals import post_save
from statements.models import BankStatement
from statements.tasks import process_uploaded_statement

@receiver(post_save, sender=BankStatement)
def statement_processing(sender, instance, created, **kwargs):
  if created:
    if instance.status == 'uploaded':  
      process_uploaded_statement.delay(str(instance.id))