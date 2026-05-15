from django.dispatch import receiver
from django.db.models.signals import post_save
from rates.models import ExchangeRate
from rates.services import RateCacheService
import requests
from parent.circuit_utils import breaker_call, LEDGER_BREAKER
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

@receiver(post_save, sender=ExchangeRate)
def handle_rate_update(sender, instance, created, **kwargs):
  if created:
    cache_service = RateCacheService()
    cache_key = f'forex:rate:{instance.from_currency.lower()}:{instance.to_currency.lower()}'
    cache_service.redis_client.delete(cache_key)
        
    record_url = 'http://localhost:8003/events/event/append/'
    payload = {'event_type': 'RATE_UPDATED', 'aggregate_id': str(instance.id), 'aggregate_type': 'wallet', 'payload': {'from_currency': instance.from_currency, 'to_currency': instance.to_currency, 'rate': str(instance.rate), 'source': instance.source,
      'effective_from': instance.effective_from.isoformat()}}
    headers = {'X-Internal-Service-Key': settings.INTERNAL_SERVICE_SECRET}
    response, error = breaker_call(LEDGER_BREAKER, requests.post, record_url, headers=headers, json=payload, timeout=1)
    if error:
      logger.error('the record serv is unavail during rate update %s/%s: %s', instance.from_currency, instance.to_currency, error)