from rest_framework import serializers
from transactions.serializers.basic import TransactionSerializer1
from refunds.models import Refund

class RefundDetailSerializer(serializers.ModelSerializer):
  status_display = serializers.CharField(source = 'get_status_display', read_only=True)
  refund_transaction_details = TransactionSerializer1(source = 'refund_transaction', read_only=True)
  class Meta:
    model = Refund
    fields = ['id', 'original_transaction_id', 'refund_transaction', 'refund_transaction_details', 'amount', 'reason',
      'status', 'status_display', 'requested_by', 'approved_by', 'created_at', 'updated_at']
    read_only_fields = fields
    
class RefundRequestSerializer(serializers.Serializer):
  transaction_id = serializers.UUIDField(required=True)
  amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
  reason = serializers.CharField(max_length=500, required=True)

  def validate_amount(self, value):
    if value <= 0:
      raise serializers.ValidationError('the refund amount s/h be > than zero.')
    return value