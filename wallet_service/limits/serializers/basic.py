from rest_framework import serializers
from limits.models import DailySpending, MonthlySpending, FraudFlag

class DailySpendingSerializer(serializers.ModelSerializer):
  class Meta:
    model = DailySpending
    fields = ['id', 'wallet', 'date', 'total_spent', 'transaction_count']
    read_only_fields = fields

class MonthlySpendingSerializer(serializers.ModelSerializer):
  class Meta:
    model = MonthlySpending
    fields = ['id', 'wallet', 'year', 'month', 'total_spent', 'transaction_count']
    read_only_fields = fields
    
class FraudFlagSerializer1(serializers.ModelSerializer):
  wallet_id = serializers.UUIDField(source = 'wallet.user_id', read_only=True)
  reason_display = serializers.CharField(source = 'get_reason_display', read_only=True)
  class Meta:
    model = FraudFlag
    fields = ['id', 'wallet_id', 'reason', 'reason_display', 'is_resolved', 'created_at']