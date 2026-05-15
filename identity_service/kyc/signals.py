from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import KYCProfile
import json, hmac, hashlib, requests
from django.conf import settings
from parent.circuit_utils import breaker_call, WALLET_BREAKER
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=KYCProfile)
def trigger_wallet_upgrade(sender, instance, created, **kwargs):
  if instance.status != 'approved':
    return
  if not instance.is_verified:
    return
  url = f'http://127.0.0.1:8001/wallets/wallet/{instance.user.id}/upgrade_tier/'
  secret = getattr(settings, 'INTERNAL_SERVICE_SECRET', 'pak_remit_secret_2026')
  payload = {'tier': instance.tier}
  payload_str = json.dumps(payload, sort_keys=True)
  signature = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
  headers = {'X-Internal-Token': secret, 'X-Internal-Signature': signature, 'Content-Type': 'application/json'}
  response, error = breaker_call(WALLET_BREAKER, requests.patch, url, json=payload, headers=headers, timeout=5)
  if error:
    logger.error('the wallet tier upgrade failed for user %s: %s', instance.user.id, error)