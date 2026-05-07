from rest_framework import serializers
from kyc.models import KYCProfile, VerificationLog

class VerificationLogSerializer(serializers.ModelSerializer):
  class Meta:
    model = VerificationLog
    fields = ['id', 'method', 'status', 'metadata', 'created_at']

class KYCDetailSerializer(serializers.ModelSerializer):
  records = VerificationLogSerializer(many=True, read_only=True)
  user_email = serializers.EmailField(source = 'user.email', read_only=True)
  verified_by_email = serializers.EmailField(source = 'verified_by.email', read_only=True)

  class Meta:
    model = KYCProfile
    fields = ['id', 'user_email', 'status', 'tier', 'cnic_front_image', 'cnic_back_image', 'utility_bill_image',
      'is_biometric_verified', 'is_verified', 'verified_at', 'verified_by_email', 'expires_at', 'rej_reason',
      'records', 'created_at', 'updated_at']
    read_only_fields = fields 