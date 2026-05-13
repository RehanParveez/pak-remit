from django.db import models
from parent.models import BaseModel

class BankStatement(BaseModel):
  STATUS_CHOICES = (
    ('uploaded', 'Uploaded'),
    ('processing', 'Processing'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
  )
    
  BANK_CHOICES = (
    ('hbl', 'HBL'),
    ('ubl', 'UBL'),
    ('mcb', 'MCB'),
    ('allied', 'Allied'),
    ('fb', 'FB'),
  )
  bank_name = models.CharField(max_length=110, choices=BANK_CHOICES)
  account_number = models.CharField(max_length=60)
  statement_date = models.DateField()
  opening_balance = models.DecimalField(max_digits=22, decimal_places=2)
  closing_balance = models.DecimalField(max_digits=22, decimal_places=2)
  file = models.FileField(upload_to = 'bank_statements/')
  status = models.CharField(max_length=30, choices=STATUS_CHOICES, default = 'uploaded')
    
  class Meta:
    indexes = [models.Index(fields=['bank_name', 'account_number']), models.Index(fields=['statement_date']),
      models.Index(fields=['status'])]
    ordering = ['-statement_date']
    
  def __str__(self):
    return f'{self.bank_name}'

class BankTransaction(BaseModel):
  TYPE_CHOICES = (
    ('debit', 'Debit'),
    ('credit', 'Credit'),
  )
  statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name = 'transactions')
  transaction_date = models.DateField()
  amount = models.DecimalField(max_digits=30, decimal_places=2)
  description = models.TextField()
  reference_number = models.CharField(max_length=110, blank=True, null=True)
  transaction_type = models.CharField(max_length=14, choices=TYPE_CHOICES)
    
  class Meta:
    indexes = [models.Index(fields=['statement', 'transaction_date']), models.Index(fields=['reference_number']),
      models.Index(fields=['amount'])]
    ordering = ['transaction_date']
    
  def __str__(self):
    return f'{self.transaction_type} {self.amount} on {self.transaction_date}'

class SettlementMatch(BaseModel):
  STATUS_CHOICES = (
    ('matched', 'Matched'),
    ('unmatched', 'Unmatched'),
    ('disputed', 'Disputed'),
  )
  internal_transaction_id = models.UUIDField()
  bank_transaction = models.ForeignKey(BankTransaction, on_delete=models.CASCADE, related_name = 'matches')
  match_confidence = models.IntegerField(default=0)
  status = models.CharField(max_length=30, choices=STATUS_CHOICES, default = 'matched')
    
  class Meta:
    indexes = [models.Index(fields=['internal_transaction_id']), models.Index(fields=['status']),
      models.Index(fields=['match_confidence'])]
    
  def __str__(self):
    return f'match {self.internal_transaction_id}'

class SettlementDifference(BaseModel):
  internal_transaction_id = models.UUIDField(null=True, blank=True)
  bank_transaction = models.ForeignKey(BankTransaction, on_delete=models.CASCADE, related_name = 'differences')
  difference_amount = models.DecimalField(max_digits=30, decimal_places=2)
  reason = models.TextField()
  is_resolved = models.BooleanField(default=False)
  resolution_notes = models.TextField(blank=True, null=True)
    
  class Meta:
    indexes = [models.Index(fields=['is_resolved']), models.Index(fields=['internal_transaction_id'])]
    
  def __str__(self):
    return f'difference {self.difference_amount}'