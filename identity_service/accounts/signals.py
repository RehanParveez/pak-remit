from django.dispatch import receiver
from django.db.models.signals import post_save
from accounts.models import User
from django.conf import settings
import json
import hmac
import hashlib
import requests
from parent.circuit_utils import breaker_call, WALLET_BREAKER
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def trigger_wallet_creation(sender, instance, created, **kwargs):
  if not created:
    return
  url = 'http://127.0.0.1:8001/wallets/wallet/create-internal/'
  secret_key = getattr(settings, 'INTERNAL_SERVICE_SECRET', 'pak_remit_secret_2026')
  
  payload = {'user_id': str(instance.id), 'currency': 'PKR', 'initial_balance': '0.00'}
  payload_str = json.dumps(payload, sort_keys=True)
  signature = hmac.new(secret_key.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
  headers = {'X-Internal-Token': secret_key, 'X-Internal-Signature': signature, 'Content-Type': 'application/json'}
  response, error = breaker_call(WALLET_BREAKER, requests.post, url, data=payload_str, headers=headers, timeout=5)
  if error:
    logger.error('the wallet crea failed for user %s: %s', instance.id, error)
  elif response and response.status_code != 201:
    logger.error('the wallet crea failed for user %s: status %s', instance.id, response.status_code)