from django.db import models
from parent.models import BaseModel
from django.utils import timezone

class Transaction(BaseModel):
  CURRENCY_CHOICES = (
    ('pkr', 'PKR'),
    ('usd', 'USD'),
    ('eur', 'EUR'),
    ('gbp', 'GBP'),
  )
  
  STATUS_CHOICES = (
    ('initiated', 'Initiated'),
    ('validating', 'Validating'),
    ('processing', 'Processing'),
    ('clearing', 'Clearing'),
    ('settled', 'Settled'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('refunded', 'Refunded'),
  )

  TYPE_CHOICES = (
    ('p2p', 'P2P'),
    ('merchant', 'Merchant'),
    ('bill', 'Bill'),
    ('remittance', 'Remittance'),
    ('refund', 'Refund'),
  )
  from_wallet_id = models.UUIDField()
  to_wallet_id = models.UUIDField()
  amount = models.DecimalField(max_digits=12, decimal_places=2)
  currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default = 'pkr')
  status = models.CharField(max_length=20, choices=STATUS_CHOICES, default = 'initiated')
  transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
  idempotency_key = models.CharField(max_length=270, unique=True)
  settled_at = models.DateTimeField(null=True, blank=True)
  completed_at = models.DateTimeField(null=True, blank=True)

  class Meta:
    indexes = [models.Index(fields=['idempotency_key']), models.Index(fields=['from_wallet_id']),
      models.Index(fields=['to_wallet_id']), models.Index(fields=['status']), models.Index(fields=['created_at'])]

  def __str__(self):
    return f'{self.transaction_type} | {self.id} | {self.status}'

class TransactionFee(BaseModel):
  transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name = 'fee')
  base_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
  percentage_fee = models.DecimalField(max_digits=7, decimal_places=2, default=0.00)
  total_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
  currency = models.CharField(max_length=3, choices=Transaction.CURRENCY_CHOICES, default = 'pkr')

  def __str__(self):
    return f'fee for {self.transaction.id}: {self.total_fee}'

class TransactionMetadata(BaseModel):
  transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name = 'metadata')
  description = models.TextField(blank=True, null=True)
  merchant_name = models.CharField(max_length=270, blank=True, null=True)
  invoice_id = models.CharField(max_length=270, blank=True, null=True)
  external_ref = models.CharField(max_length=270, blank=True, null=True)

  def __str__(self):
    return f'metadata for {self.transaction.id}'