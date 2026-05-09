from django.contrib import admin
from limits.models import DailySpending, MonthlySpending, FraudFlag

@admin.register(DailySpending)
class DailySpendingAdmin(admin.ModelAdmin):
  list_display = ['wallet', 'date', 'total_spent', 'transaction_count', 'created_at', 'updated_at']

@admin.register(MonthlySpending)
class MonthlySpendingAdmin(admin.ModelAdmin):
  list_display = ['wallet', 'year', 'month', 'total_spent', 'transaction_count', 'created_at', 'updated_at']
  
@admin.register(FraudFlag)
class FraudFlagAdmin(admin.ModelAdmin):
  list_display = ['wallet', 'reason', 'metadata', 'is_resolved', 'resolved_at', 'resolved_by', 'created_at', 'updated_at']