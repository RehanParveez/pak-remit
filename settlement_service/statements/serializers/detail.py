from rest_framework import serializers
from statements.models import BankTransaction, SettlementMatch, BankStatement, SettlementDifference

class BankTransactionSerializer(serializers.ModelSerializer):
  class Meta:
    model = BankTransaction
    fields = ['id', 'transaction_date', 'amount', 'description', 'reference_number', 'transaction_type', 'created_at', 'updated_at']
    read_only_fields = ['id', 'created_at', 'updated_at']

class SettlementMatchSerializer(serializers.ModelSerializer):
  bank_transaction = BankTransactionSerializer(read_only=True)
  class Meta:
    model = SettlementMatch
    fields = ['id', 'internal_transaction_id', 'bank_transaction', 'match_confidence', 'status', 'created_at', 'updated_at']
    read_only_fields = ['id', 'created_at', 'updated_at']

class BankStatementSerializer(serializers.ModelSerializer):
  transactions = BankTransactionSerializer(many=True, read_only=True)
  transaction_count = serializers.SerializerMethodField()
  matched_count = serializers.SerializerMethodField() 
  class Meta:
    model = BankStatement
    fields = ['id', 'bank_name', 'account_number', 'statement_date', 'opening_balance', 'closing_balance', 'file', 'status', 'transaction_count', 'matched_count',
      'created_at', 'updated_at']
    read_only_fields = ['id', 'status', 'created_at', 'updated_at']
    
  def get_transaction_count(self, obj):
    return obj.transactions.count()
    
  def get_matched_count(self, obj):
    return SettlementMatch.objects.filter(bank_transaction__statement=obj, status = 'matched').count()

class SettlementDifferenceSerializer(serializers.ModelSerializer):
  bank_transaction = BankTransactionSerializer(read_only=True)
  class Meta:
    model = SettlementDifference
    fields = ['id', 'internal_transaction_id', 'bank_transaction', 'difference_amount', 'reason', 'is_resolved', 'resolution_notes', 'created_at', 'updated_at']
    read_only_fields = ['id', 'created_at', 'updated_at']