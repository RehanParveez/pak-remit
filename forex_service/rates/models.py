from django.db import models
from parent.models import BaseModel

class CurrencyPair(BaseModel):
  CURRENCY_CHOICES = (
    ('pkr', 'PKR'),
    ('usd', 'USD'),
    ('gbp', 'GBP'),
    ('eur', 'EUR'),
    ('aed', 'AED'),
    ('cad', 'CAD'),
    ('aud', 'AUD'),
  )
  base_currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES)
  quote_currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES)
  is_active = models.BooleanField(default=True)
    
  class Meta:
    unique_together = ('base_currency', 'quote_currency')
    indexes = [models.Index(fields=['base_currency', 'quote_currency']), models.Index(fields=['is_active'])]
    
  def __str__(self):
    return self.base_currency.upper()

class ExchangeRate(BaseModel):
  PROVIDER_CHOICES = (
    ('manual', 'Manual'),
    ('host', 'Host'),
    ('open', 'Open'),
    ('sbp', 'SBP'),
  ) 
  from_currency = models.CharField(max_length=4)
  to_currency = models.CharField(max_length=4)
  rate = models.DecimalField(max_digits=20, decimal_places=6)
  effective_from = models.DateTimeField()
  effective_until = models.DateTimeField(null=True, blank=True)
  source = models.CharField(max_length=50, choices=PROVIDER_CHOICES, default = 'manual')
    
  class Meta:
    unique_together = ('from_currency', 'to_currency', 'effective_from')
    indexes = [models.Index(fields=['from_currency', 'to_currency', 'effective_from']), models.Index(fields=['effective_from']), models.Index(fields=['source'])]
    ordering = ['-effective_from']
    
  def __str__(self):
    return str(self.rate)