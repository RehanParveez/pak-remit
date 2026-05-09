from django.db import models
from parent.models import BaseModel 
from django.utils import timezone

class DailySpending(BaseModel):
  wallet = models.ForeignKey('wallets.Wallet', on_delete=models.CASCADE, related_name = 'daily_spendings')
  date = models.DateField(default=timezone.now)
  total_spent = models.DecimalField(max_digits=40, decimal_places=2, default=0.00)
  transaction_count = models.IntegerField(default=0)
  
  class Meta:
    unique_together = ('wallet', 'date')
    indexes = [models.Index(fields=['wallet', 'date'])]

  def __str__(self):
    return f'{self.wallet.user_id} - {self.date}: {self.total_spent}'

class MonthlySpending(BaseModel):
  wallet = models.ForeignKey('wallets.Wallet', on_delete=models.CASCADE, related_name = 'monthly_spendings')
  year = models.IntegerField()
  month = models.IntegerField()
  total_spent = models.DecimalField(max_digits=40, decimal_places=2, default=0.00)
  transaction_count = models.IntegerField(default=0)

  class Meta:
    unique_together = ('wallet', 'year', 'month')
    indexes = [models.Index(fields=['wallet', 'year', 'month'])]

  def __str__(self):
    return f'{self.wallet.user_id} {self.month}/{self.year}: {self.total_spent}'

class FraudFlag(BaseModel):
  REASON_CHOICES = (
    ('rapid', 'Rapid'),
    ('large', 'Large'),
    ('unusual', 'Unusual'),
  )
  wallet = models.ForeignKey('wallets.Wallet', on_delete=models.CASCADE, related_name = 'fraud_flags')
  reason = models.CharField(max_length=50, choices=REASON_CHOICES)
  metadata = models.JSONField(default=dict, help_text = 'transaction details context.')
  is_resolved = models.BooleanField(default=False)
  resolved_at = models.DateTimeField(null=True, blank=True)
  resolved_by = models.UUIDField(null=True, blank=True, help_text = 'admin user id')

  def __str__(self):
    return f'fraud {self.reason}'