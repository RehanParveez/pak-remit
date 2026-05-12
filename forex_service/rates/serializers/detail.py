from rest_framework import serializers
from rates.models import ExchangeRate, CurrencyPair

class ExchangeRateSerializer(serializers.ModelSerializer):
  pair = serializers.SerializerMethodField()

  class Meta:
    model = ExchangeRate
    fields = ['id', 'from_currency', 'to_currency', 'pair', 'rate', 'effective_from', 'effective_until', 'source', 'created_at', 'updated_at']
    read_only_fields = ['id', 'created_at', 'updated_at']

  def get_pair(self, obj):
    return f'{obj.from_currency.upper()}/{obj.to_currency.upper()}'

class CurrencyPairSerializer(serializers.ModelSerializer):
  class Meta:
    model = CurrencyPair
    fields = ['id', 'base_currency', 'quote_currency', 'is_active', 'created_at', 'updated_at']
    read_only_fields = ['id', 'created_at', 'updated_at']