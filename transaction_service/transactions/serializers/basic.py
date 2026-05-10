from rest_framework import serializers
from transactions.models import Transaction

class TransactionSerializer1(serializers.ModelSerializer):
  status_display = serializers.CharField(source = 'get_status_display', read_only=True)
  type_display = serializers.CharField(source = 'get_transaction_type_display', read_only=True)
  class Meta: 
    model = Transaction
    fields = ['id', 'amount', 'currency', 'status', 'status_display', 'transaction_type', 'type_display',
      'from_wallet_id', 'to_wallet_id', 'created_at']
    read_only_fields = ['id', 'status', 'created_at']