from rest_framework import serializers
from statements.models import BankStatement

class StatementUploadSerializer(serializers.ModelSerializer):
  class Meta:
    model = BankStatement
    fields = ['bank_name', 'account_number', 'statement_date', 'opening_balance', 'closing_balance', 'file']

class DifferenceResolveSerializer(serializers.Serializer):
  resolution = serializers.CharField(max_length=500)

class StatementListSerializer(serializers.ModelSerializer):
  class Meta:
    model = BankStatement
    fields = ['id', 'bank_name', 'account_number', 'statement_date', 'status', 'created_at']
    read_only_fields = fields