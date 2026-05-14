from celery import shared_task
from django.utils import timezone
from webhooks.models import WebhookDelivery, WebhookEndpoint
from webhooks.services import WebhookService
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import json
import hmac
import hashlib
import requests

@shared_task
def retry_pending_webhooks():
  now = timezone.now()
  pending_count = WebhookDelivery.objects.filter(status = 'pending', next_retry_at__lte=now).count()
  WebhookService.retry_failed_webhooks()
  success_count = WebhookDelivery.objects.filter(status = 'sent', updated_at__gte=now).count()
  subject = 'webhook retry'
  message = f'''
retry
pending webhooks processed: {pending_count}
delivered: {success_count}
failed: {pending_count - success_count}
time: {now}

    '''
  send_mail(subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=['rehanrural@gmail.com'],
    fail_silently=False)
  return pending_count

@shared_task
def cleanup_old_deliveries():
  cutoff_date = timezone.now() - timedelta(days=30)
  deleted_count = WebhookDelivery.objects.filter(status = 'sent', created_at__lt=cutoff_date).delete()[0]
  subject = 'webhook cleanup'
  message = f'''
weekly cleanup
deleteddDeliveries: {deleted_count}
Cutoff Date: {cutoff_date}
status: completed
    '''
  send_mail(subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=['rehanrural@gmail.com'],
    fail_silently=False)
  return deleted_count

@shared_task(name='webhooks.tasks.trigger_transaction_webhook')
def trigger_transaction_webhook(transaction_id, merchant_id):
  endpoints = WebhookEndpoint.objects.filter(merchant_id=merchant_id, is_active=True, events__contains = 'transaction.completed')
  if not endpoints.exists():
    return f'no active webhooks pres {merchant_id}'
  for endpoint in endpoints:
    delivery = WebhookDelivery.objects.create(endpoint=endpoint, event_type = 'transaction.completed', payload={'transaction_id': transaction_id,
      'status': 'completed', 'timestamp': str(timezone.now())}, status='pending')
    dispatch_webhook.apply_async(args=[delivery.id], queue = 'notifications')
  return f'created & dispa. {endpoints.count()} deliveries {transaction_id}'

@shared_task(name='webhooks.tasks.dispatch_webhook')
def dispatch_webhook(delivery_id):
  try:
    delivery = WebhookDelivery.objects.get(id=delivery_id)
  except WebhookDelivery.DoesNotExist:
    return f"Delivery {delivery_id} not found."
  endpoint = delivery.endpoint
  payload_data = json.dumps(delivery.payload)
  signature = hmac.new(endpoint.secret.encode(), payload_data.encode(), hashlib.sha256 ).hexdigest()
  headers = {'Content-Type': 'application/json', 'X-PakRemit-Signature': signature, 'User-Agent': 'PakRemit-Webhook-Dispatcher/1.0'}

  try:
    response = requests.post(endpoint.url, data=payload_data, headers=headers, timeout=10)
    delivery.status = 'sent' if response.status_code < 400 else 'failed'
    delivery.response_code = response.status_code
    delivery.response_body = response.text[:1000] 
  except requests.exceptions.RequestException as e:
    delivery.status = 'failed'
    delivery.response_body = str(e)
  delivery.updated_at = timezone.now()
  delivery.save()
  return f'delivery {delivery_id} status {delivery.status}'