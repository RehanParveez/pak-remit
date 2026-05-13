from rest_framework import serializers
from webhooks.models import WebhookEndpoint, WebhookDelivery

class WebhookEndpointSerializer(serializers.ModelSerializer):
  class Meta:
    model = WebhookEndpoint
    fields = ['id', 'merchant_id', 'url', 'events', 'secret', 'is_active', 'created_at']
    read_only_fields = ['id', 'secret', 'created_at']

class WebhookDeliverySerializer(serializers.ModelSerializer):
  endpoint_url = serializers.CharField(source = 'endpoint.url', read_only=True)
  class Meta:
    model = WebhookDelivery
    fields = ['id', 'endpoint', 'endpoint_url', 'event_type', 'payload', 'status', 'attempts', 'next_retry_at', 'response_code', 'response_body', 'created_at']
    read_only_fields = ['id', 'created_at']