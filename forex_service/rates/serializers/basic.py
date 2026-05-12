from rest_framework import serializers
from rates.models import CurrencyPair

class RateUpdateSerializer(serializers.Serializer):
  from_currency = serializers.CharField(max_length=4)
  to_currency = serializers.CharField(max_length=4)
  rate = serializers.DecimalField(max_digits=18, decimal_places=6)
  source = serializers.ChoiceField(choices=['manual', 'host', 'open', 'sbp'], default = 'manual')

class CurrencyConversionSerializer(serializers.Serializer):
  amount = serializers.DecimalField(max_digits=18, decimal_places=2)
  from_currency = serializers.CharField(max_length=4)
  to_currency = serializers.CharField(max_length=4)

  def validate(self, data):
    exists = CurrencyPair.objects.filter(base_currency=data['from_currency'].lower(), quote_currency=data['to_currency'].lower(), is_active=True).exists()
    if not exists:
      raise serializers.ValidationError('this curr pair is not active or supp.')
            
    return data