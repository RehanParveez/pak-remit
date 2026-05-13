from django.contrib import admin
from transactions.models import Transaction, TransactionFee, TransactionMetadata

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
  list_display = ['id', 'from_wallet_id', 'to_wallet_id', 'amount', 'currency', 'status', 'transaction_type', 'idempotency_key', 'settled_at', 
    'completed_at', 'created_at', 'updated_at', 'merchant_id']
  list_filter = ['status', 'transaction_type', 'currency', 'created_at']
  search_fields = ['id', 'idempotency_key', 'from_wallet_id', 'to_wallet_id']
  readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(TransactionFee)
class TransactionFeeAdmin(admin.ModelAdmin):
  list_display = ['id', 'transaction', 'base_fee', 'percentage_fee', 'total_fee', 'currency', 'created_at', 'updated_at']
  readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(TransactionMetadata)
class TransactionMetadataAdmin(admin.ModelAdmin):
  list_display = ['id', 'transaction', 'description', 'merchant_name', 'invoice_id', 'external_ref', 'created_at', 'updated_at']
  readonly_fields = ['id', 'created_at', 'updated_at']