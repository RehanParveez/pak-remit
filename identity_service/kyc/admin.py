from django.contrib import admin
from kyc.models import KYCProfile, VerificationLog

@admin.register(KYCProfile)
class KYCProfileAdmin(admin.ModelAdmin):
  list_display = ['id', 'user', 'status', 'tier', 'cnic_front_image', 'cnic_back_image', 'utility_bill_image', 'biometric_hash', 'is_biometric_verified', 'is_verified', 'verified_at', 'verified_by', 'expires_at', 'rej_reason', 'created_at', 'updated_at']
  
@admin.register(VerificationLog)
class VerificationLogAdmin(admin.ModelAdmin):
  list_display = ['id', 'kyc_profile', 'method', 'status', 'metadata', 'verified_by', 'created_at', 'updated_at']
