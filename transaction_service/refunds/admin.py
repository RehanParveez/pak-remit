from django.contrib import admin
from refunds.models import Refund

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
  list_display = ['original_transaction_id', 'refund_transaction', 'amount', 'reason', 'status', 'requested_by', 'approved_by', 'created_at', 'updated_at']