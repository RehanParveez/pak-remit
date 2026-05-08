from rest_framework import serializers
from wallets.models import WalletLimit, Wallet

class WalletLimitSerializer1(serializers.ModelSerializer):
  class Meta:
    model = WalletLimit
    fields = ['tier', 'daily_limit', 'monthly_limit', 'transaction_limit', 'updated_at']
    read_only_fields = fields 

class InternalWalletCreateSerializer(serializers.Serializer):
  user_id = serializers.UUIDField()
  currency = serializers.ChoiceField(choices=Wallet.CURRENCY_CHOICES, default = 'pkr')