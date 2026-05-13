from rest_framework import serializers
from webhooks.models import WebhookEndpoint

class WebhookRegisterSerializer(serializers.ModelSerializer):
  class Meta:
    model = WebhookEndpoint
    fields = ['url', 'events']

class WebhookListSerializer(serializers.ModelSerializer):
  class Meta:
    model = WebhookEndpoint
    fields = ['id', 'url', 'events', 'is_active', 'created_at']
    read_only_fields = fields