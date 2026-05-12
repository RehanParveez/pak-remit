import redis
from django.conf import settings
from decimal import Decimal
from rates.models import ExchangeRate, CurrencyPair
from django.utils import timezone

class RateCacheService:
  def __init__(self):
    self.redis_client = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=6, decode_responses=True)
    self.ttl = 3600

  def _get_key(self, from_curr, to_curr):
    return f'forex:rate:{from_curr.lower()}:{to_curr.lower()}'

  def cache_rate(self, from_currency, to_currency, rate):
    key = self._get_key(from_currency, to_currency)
    self.redis_client.setex(key, self.ttl, str(rate))

  def get_cached_rate(self, from_currency, to_currency):
    key = self._get_key(from_currency, to_currency)
    return self.redis_client.get(key)

class ForexService:
  def __init__(self):
    self.cache = RateCacheService()

  def get_current_rate(self, from_currency, to_currency):
    cached_rate = self.cache.get_cached_rate(from_currency, to_currency)
    if cached_rate:
      return Decimal(cached_rate)
    rate_obj = ExchangeRate.objects.filter(from_currency=from_currency.lower(), to_currency=to_currency.lower(),
      effective_from__lte=timezone.now()).order_by('-effective_from').first()

    if rate_obj:
      self.cache.cache_rate(from_currency, to_currency, rate_obj.rate)
      return rate_obj.rate
        
    return None

  def convert_amount(self, amount, from_currency, to_currency):
    is_active = CurrencyPair.objects.filter(base_currency=from_currency.lower(), quote_currency=to_currency.lower(), is_active=True
    ).exists()
    if not is_active:
      raise ValueError(f'curre. pair {from_currency}/{to_currency} is not currently supp or active.')
    rate = self.get_current_rate(from_currency, to_currency)
    if not rate:
      raise ValueError(f'no exchange rate pres for {from_currency}/{to_currency}')
    return (Decimal(amount) * rate).quantize(Decimal('0.01'))

  def get_historical_rate(self, from_currency, to_currency, date):
    rate_obj = ExchangeRate.objects.filter(from_currency=from_currency.lower(), to_currency=to_currency.lower(),
      effective_from__lte=date).order_by('-effective_from').first()
    return rate_obj.rate if rate_obj else None

  def fetch_live_rates(self):
    print('fetch. the live rates from the exter. provided...')
    pass