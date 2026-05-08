from rest_framework import serializers
from wallets.models import WalletLimit, WalletBookings, Wallet
from wallets.serializers.basic import WalletLimitSerializer1

class WalletLimitSerializer(serializers.ModelSerializer):
  class Meta:
    model = WalletLimit
    fields = ['tier', 'daily_limit', 'monthly_limit', 'transaction_limit', 'created_at', 'updated_at']
    read_only_fields = fields 
        
class WalletBookingSerializer(serializers.ModelSerializer):
  class Meta:
    model = WalletBookings
    fields = ['id', 'amount', 'reason', 'reserved_at', 'expires_at', 'is_released', 'is_committed', 'created_at', 'updated_at']
    read_only_fields = fields
        
class WalletSerializer(serializers.ModelSerializer):
  limit = WalletLimitSerializer1(read_only=True)
  class Meta:
    model = Wallet
    fields = ['id', 'user_id', 'currency', 'balance', 'reserved_balance', 'available_balance', 'status', 'limit', 'created_at', 'updated_at']
    read_only_fields = ['id', 'user_id', 'currency', 'balance', 'available_balance', 'created_at', 'updated_at']