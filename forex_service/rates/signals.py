from django.dispatch import receiver
from django.db.models.signals import post_save
from rates.models import ExchangeRate
from rates.services import RateCacheService
import requests

@receiver(post_save, sender=ExchangeRate)
def handle_rate_update(sender, instance, created, **kwargs):
  if created:
    cache_service = RateCacheService()
    cache_key = f'forex:rate:{instance.from_currency.lower()}:{instance.to_currency.lower()}'
    cache_service.redis_client.delete(cache_key)
        
    record_url = 'http://localhost:8003/events/event/append/'
    payload = {'from_currency': instance.from_currency, 'to_currency': instance.to_currency, 'rate': str(instance.rate), 'source': instance.source,
      'effective_from': instance.effective_from.isoformat()}
    requests.post(record_url, json=payload, timeout=1)