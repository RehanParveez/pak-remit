from django.db import models
from parent.models import BaseModel
from transactions.models import Transaction

class Refund(BaseModel):
  STATUS_CHOICES = (
    ('requested', 'Requested'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('completed', 'Completed'),
  )
  original_transaction_id = models.UUIDField(db_index=True)
  refund_transaction = models.UUIDField(null=True, blank=True, db_index=True)
  amount = models.DecimalField(max_digits=14, decimal_places=2)
  reason = models.TextField()
  status = models.CharField(max_length=25, choices=STATUS_CHOICES, default = 'requested')
  requested_by = models.UUIDField() 
  approved_by = models.UUIDField(null=True, blank=True)

  class Meta:
    indexes = [models.Index(fields=['original_transaction_id']), models.Index(fields=['status']),
      models.Index(fields=['requested_by'])]

    def __str__(self):
        return f'{self.id} | Status: {self.status}'