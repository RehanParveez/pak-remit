from rest_framework import serializers
from transactions.models import Transaction, TransactionFee, TransactionMetadata

class TransactionFeeSerializer(serializers.ModelSerializer):
  class Meta:
    model = TransactionFee
    fields = ['base_fee', 'percentage_fee', 'total_fee', 'currency', 'created_at', 'updated_at']
    read_only_fields = ['created_at', 'updated_at']

class TransactionMetadataSerializer(serializers.ModelSerializer):
  class Meta:
    model = TransactionMetadata
    fields = ['description', 'merchant_name', 'invoice_id', 'external_ref', 'created_at', 'updated_at']
    read_only_fields = ['created_at', 'updated_at']

class TransactionSerializer(serializers.ModelSerializer):
  fee = TransactionFeeSerializer(read_only=True)
  metadata = TransactionMetadataSerializer(read_only=True)
  status_display = serializers.CharField(source = 'get_status_display', read_only=True)
  type_display = serializers.CharField(source = 'get_transaction_type_display', read_only=True)
  class Meta:
    model = Transaction
    fields = ['id', 'from_wallet_id', 'to_wallet_id', 'amount', 'currency', 'status', 'status_display',
      'transaction_type', 'type_display', 'idempotency_key', 'fee', 'metadata', 'settled_at', 'completed_at', 'created_at', 'updated_at', 'trace_id']
        
    read_only_fields = fields