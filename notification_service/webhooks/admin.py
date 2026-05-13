from django.contrib import admin
from webhooks.models import WebhookEndpoint, WebhookDelivery

@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
  list_display = ['merchant_id', 'url', 'events', 'secret', 'is_active']
  list_filter = ('is_active',)
  search_fields = ('merchant_id', 'url')
  readonly_fields = ('secret',)

@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
  list_display = ['endpoint', 'event_type', 'payload', 'status', 'attempts', 'next_retry_at', 'response_code', 'response_body']
  list_filter = ('status', 'event_type', 'created_at')
  search_fields = ('event_type', 'response_code')
#   readonly_fields = ('payload', 'response_body')