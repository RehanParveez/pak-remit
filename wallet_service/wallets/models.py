from django.db import models
from parent.models import BaseModel

class Wallet(BaseModel):
  STATUS_CHOICES = (
    ('active', 'Active'),
    ('frozen', 'Frozen'),
    ('suspended', 'Suspended'),
  )
  
  CURRENCY_CHOICES = (
    ('pkr', 'PKR'),
    ('usd', 'USD'),
    ('gbp', 'GBP'),
    ('aed', 'AED'),
  )
  user_id = models.UUIDField(db_index=True)
  currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default = 'pkr') 
  balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
  reserved_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
  status = models.CharField(max_length=15, choices=STATUS_CHOICES, default = 'active')

  class Meta:
    unique_together = ('user_id', 'currency')
    indexes = [models.Index(fields=['currency', 'user_id'])]

  @property
  def available_balance(self):
    return self.balance - self.reserved_balance

  def __str__(self):
    return f'{self.user_id}'

class WalletLimit(BaseModel):
  TIER_CHOICES = (
    ('tier1', 'Tier1'),
    ('tier2', 'Tier2'),
    ('tier3', 'Tier3'),
  )
  wallet = models.OneToOneField(Wallet, on_delete=models.CASCADE, related_name = 'limit')
  tier = models.CharField(choices=TIER_CHOICES, default = 'tier1')
  daily_limit = models.DecimalField(max_digits=30, decimal_places=2, default=20000.00)
  monthly_limit = models.DecimalField(max_digits=30, decimal_places=2, default=5000000.00)
  transaction_limit = models.DecimalField(max_digits=30, decimal_places=2, default=10000.00)
  daily_spent = models.DecimalField(max_digits=30, decimal_places=2, default=0.00)
  
  def __str__(self):
    return f'limit for {self.wallet.user_id}'

class WalletBookings(BaseModel):
  wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name = 'bookings')
  amount = models.DecimalField(max_digits=30, decimal_places=2)
  reason = models.CharField(max_length=270)
  reserved_at = models.DateTimeField(auto_now_add=True) 
  expires_at = models.DateTimeField()
  is_released = models.BooleanField(default=False)
  is_committed = models.BooleanField(default=False) 

  def __str__(self):
    return f'booking {self.amount} for {self.wallet.user_id}'

class WalletRecord(BaseModel):
  ENTRY_TYPES = (
    ('credit', 'Credit'),
    ('debit', 'Debit')
  )
  wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name = 'record')
  amount = models.DecimalField(max_digits=30, decimal_places=2)
  type = models.CharField(max_length=12, choices=ENTRY_TYPES)
  description = models.CharField(max_length=270)
  
  def __str__(self):
    return f'{self.type.capitalize()} of {self.amount} user {self.wallet.user_id}'