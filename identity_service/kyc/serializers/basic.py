from rest_framework import serializers
from kyc.models import KYCProfile

class KYCSerializer1(serializers.ModelSerializer):
  class Meta:
    model = KYCProfile
    fields = ['cnic_front_image', 'cnic_back_image', 'utility_bill_image']
    extra_kwargs = {'cnic_front_image': {'required': True}, 'cnic_back_image': {'required': True}}

  def validate(self, attrs):
    user = self.context['request'].user
    if hasattr(user, 'kyc_profile'):
      if user.kyc_profile.status in ['pending', 'approved']:
        raise serializers.ValidationError(f'KYC is already {user.kyc_profile.status}. cant resubmit')
    return attrs