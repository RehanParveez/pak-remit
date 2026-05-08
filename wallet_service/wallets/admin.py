from django.contrib import admin
from wallets.models import Wallet, WalletLimit, WalletBookings

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
  list_display = ['user_id', 'currency', 'balance', 'reserved_balance', 'available_balance', 'status', 'created_at', 'updated_at']

@admin.register(WalletLimit)
class WalletLimit(admin.ModelAdmin):
  list_display = ['wallet', 'tier', 'daily_limit', 'monthly_limit', 'transaction_limit', 'created_at', 'updated_at']
  
@admin.register(WalletBookings)
class WalletBookings(admin.ModelAdmin):
  list_display = ['wallet', 'amount', 'reason', 'reserved_at', 'expires_at', 'is_released', 'is_committed', 'created_at', 'updated_at']