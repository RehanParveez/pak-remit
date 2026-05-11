from rest_framework import serializers
from refunds.models import Refund
from refunds.services import RefundService
from transactions.serializers.basic import TransactionSerializer1

class RefundDetailSerializer(serializers.ModelSerializer):
  status_display = serializers.CharField(source = 'get_status_display', read_only=True)
  refund_transaction_details = serializers.SerializerMethodField()
  class Meta:
    model = Refund
    fields = ['id', 'original_transaction_id', 'refund_transaction', 'refund_transaction_details', 'amount', 'reason',
      'status', 'status_display', 'requested_by', 'approved_by', 'created_at', 'updated_at']
    read_only_fields = fields
    
  def get_refund_transaction_details(self, obj):
    if not obj.refund_transaction:
      return None
    tx_obj = RefundService._find_original_transaction(obj.refund_transaction)
    if tx_obj:
      return TransactionSerializer1(tx_obj).data
    return None  
    
class RefundRequestSerializer(serializers.Serializer):
  transaction_id = serializers.UUIDField(required=True)
  amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
  reason = serializers.CharField(max_length=500, required=True)

  def validate_amount(self, value):
    if value <= 0:
      raise serializers.ValidationError('the refund amount s/h be > than zero.')
    return value