from rest_framework import serializers
from limits.models import FraudFlag
from django.utils import timezone

class FraudFlagSerializer(serializers.ModelSerializer):
  wallet_details = serializers.SerializerMethodField()
  class Meta:
    model = FraudFlag
    fields = ['id', 'wallet', 'wallet_details', 'reason', 'metadata', 'is_resolved', 'resolved_at', 'resolved_by', 'created_at']
    read_only_fields = ['created_at', 'wallet']

  def get_wallet_details(self, obj):
    return {'user_id': obj.wallet.user_id, 'currency': obj.wallet.currency, 'status': obj.wallet.status}

class FraudResolutionSerializer(serializers.Serializer):
  notes = serializers.CharField(required=True, max_length=500)
  def update(self, instance, validated_data):
    instance.is_resolved = True
    instance.resolved_at = timezone.now()
    instance.resolved_by = self.context['request'].auth.get('user_id') 
    instance.metadata['resolution_notes'] = validated_data['notes']
    instance.save()
    return instance