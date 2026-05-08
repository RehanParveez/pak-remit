from django.contrib import admin
from wallets.models import Wallet, WalletLimit, WalletBookings, WalletRecord

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
  list_display = ['user_id', 'currency', 'balance', 'reserved_balance', 'available_balance', 'status', 'created_at', 'updated_at']

@admin.register(WalletLimit)
class WalletLimitAdmin(admin.ModelAdmin):
  list_display = ['wallet', 'tier', 'daily_limit', 'monthly_limit', 'transaction_limit', 'created_at', 'updated_at']
  
@admin.register(WalletBookings)
class WalletBookingsAdmin(admin.ModelAdmin):
  list_display = ['wallet', 'amount', 'reason', 'reserved_at', 'expires_at', 'is_released', 'is_committed', 'created_at', 'updated_at']
  
@admin.register(WalletRecord)
class WalletRecordAdmin(admin.ModelAdmin):
  list_display = ['wallet', 'amount', 'type', 'description', 'created_at', 'updated_at']