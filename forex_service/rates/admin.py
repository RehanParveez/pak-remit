from django.contrib import admin
from rates.models import CurrencyPair, ExchangeRate

@admin.register(CurrencyPair)
class CurrencyPairAdmin(admin.ModelAdmin):
  list_display = ['base_currency', 'quote_currency', 'is_active']
  list_filter = ('is_active', 'base_currency')
  search_fields = ('base_currency', 'quote_currency')

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
  list_display = ['from_currency', 'to_currency', 'rate', 'effective_from', 'effective_until', 'source']
  list_filter = ('source', 'from_currency', 'to_currency')
  search_fields = ('from_currency', 'to_currency', 'source')
  date_hierarchy = 'effective_from'
  readonly_fields = ('created_at', 'updated_at') 
