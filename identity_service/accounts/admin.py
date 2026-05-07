from django.contrib import admin
from accounts.models import User, Profile, UserDevice

class ProfileInline(admin.StackedInline):
    model = Profile

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
  inlines = [ProfileInline]
  list_display = ['id', 'email', 'phone', 'cnic_hash', 'control', 'failed_login_attempts', 'acc_locked_until', 'last_pass_change', 'is_deleted', 'created_at', 'updated_at']
  
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
  list_display = ['id', 'user', 'full_name', 'dob', 'address', 'city', 'country', 'is_verified', 'risk_score', 'risk_level', 'pic', 'created_at', 'updated_at']

@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
  list_display = ['id', 'user', 'device_fingerprint', 'type', 'is_trusted', 'last_login', 'last_ip', 'created_at', 'updated_at']