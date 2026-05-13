from django.contrib import admin
from statements.models import BankStatement, BankTransaction, SettlementMatch, SettlementDifference

@admin.register(BankStatement)
class BankStatementAdmin(admin.ModelAdmin):
  list_display = ['bank_name', 'account_number', 'statement_date', 'opening_balance', 'closing_balance', 
    'file', 'status']
  list_filter = ('bank_name', 'status', 'statement_date')
  search_fields = ('account_number', 'bank_name')

@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
  list_display = ['statement', 'transaction_date', 'amount', 'description', 'reference_number', 'transaction_type']
  list_filter = ('transaction_type', 'transaction_date', 'statement__bank_name')
  search_fields = ('reference_number', 'description')

@admin.register(SettlementMatch)
class SettlementMatchAdmin(admin.ModelAdmin):
  list_display = ['internal_transaction_id', 'bank_transaction', 'match_confidence', 'status']
  list_filter = ('status', 'match_confidence')
  search_fields = ('internal_transaction_id',)

@admin.register(SettlementDifference)
class SettlementDifferenceAdmin(admin.ModelAdmin):
  list_display = ['internal_transaction_id', 'bank_transaction', 'difference_amount', 'reason', 'is_resolved', 'resolution_notes']
  list_filter = ('is_resolved', 'bank_transaction__statement__bank_name')
  search_fields = ('internal_transaction_id', 'reason')