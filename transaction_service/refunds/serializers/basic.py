from rest_framework import serializers
from refunds.models import Refund

class RefundBasicSerializer(serializers.ModelSerializer):
  status_display = serializers.CharField(source='get_status_display', read_only=True)
  class Meta:
    model = Refund
    fields = ['id', 'original_transaction_id', 'amount', 'status', 'status_display', 'created_at']
    read_only_fields = fields