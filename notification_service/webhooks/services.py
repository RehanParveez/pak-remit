from webhooks.models import WebhookEndpoint, WebhookDelivery
import requests
from django.utils import timezone
from datetime import timedelta
import json
import hmac
import hashlib

class WebhookService:
  @staticmethod
  def send_webhook(endpoint_id, event_type, payload):
    endpoint = WebhookEndpoint.objects.get(id=endpoint_id)
        
    if not endpoint.is_active:
      return False
    if event_type not in endpoint.events:
      return False
    delivery = WebhookDelivery.objects.create(endpoint=endpoint, event_type=event_type, payload=payload, status = 'pending')
    signature = WebhookService._generate_signature(payload, endpoint.secret)
    headers = {'Content-Type': 'application/json', 'X-Webhook-Signature': signature, 'X-Event-Type': event_type}
    response = requests.post(endpoint.url, json=payload, headers=headers, timeout=10)
    delivery.attempts += 1
    delivery.response_code = response.status_code
    delivery.response_body = response.text[:1000]
    if response.status_code == 200:
      delivery.status = 'sent'
    else:
      delivery.status = 'failed'
      delivery.next_retry_at = timezone.now() + timedelta(seconds=30)
    delivery.save()
    return True
    
  @staticmethod
  def retry_failed_webhooks():
    now = timezone.now()
    pending = WebhookDelivery.objects.filter(status = 'pending', next_retry_at__lte=now)
    retry_delays = [30, 60, 300, 1800, 7200]
    for delivery in pending:
      if delivery.attempts >= 5:
        delivery.status = 'failed'
        delivery.save()
        continue
            
      endpoint = delivery.endpoint
      signature = WebhookService._generate_signature(delivery.payload, endpoint.secret)
      headers = {'Content-Type': 'application/json', 'X-Webhook-Signature': signature, 'X-Event-Type': delivery.event_type}
      response = requests.post(endpoint.url, json=delivery.payload, headers=headers, timeout=10)
      delivery.attempts += 1
      delivery.response_code = response.status_code
      delivery.response_body = response.text[:1000]
      if response.status_code == 200:
        delivery.status = 'sent'
        delivery.next_retry_at = None
      else:
        delay_index = min(delivery.attempts - 1, len(retry_delays) - 1)
        delivery.next_retry_at = now + timedelta(seconds=retry_delays[delay_index])
            
      delivery.save()
    
  @staticmethod
  def verify_webhook_signature(payload, signature, secret):
    expected = WebhookService._generate_signature(payload, secret)
    return hmac.compare_digest(signature, expected)
    
  @staticmethod
  def _generate_signature(payload, secret):
    message = json.dumps(payload, sort_keys=True).encode()
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return signature