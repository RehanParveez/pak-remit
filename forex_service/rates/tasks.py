from celery import shared_task
from django.utils import timezone
import uuid
import requests
from rates.models import CurrencyPair, ExchangeRate
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def fetch_live_forex_rates():
  url = 'https://api.exchangerate.host/latest'
  current_time = timezone.now()
  system_trace_id = f"sys_fetch_{uuid.uuid4().hex[:8]}"
  response = requests.get(url, params={'base': 'USD'}, timeout=10)
  data = response.json()
  rates = data.get('rates', {})
  active_pairs = CurrencyPair.objects.filter(is_active=True)
  for pair in active_pairs:
    quote = pair.quote_currency.upper()
    new_rate = rates.get(quote)
    
    if new_rate:
      ExchangeRate.objects.create(from_currency=pair.base_currency.lower(), to_currency=pair.quote_currency.lower(), rate=new_rate, source = 'host',
        effective_from=current_time, trace_id=system_trace_id)
    else:
      send_mail('missing rate alert', f'could not find live rate for {quote}.', settings.DEFAULT_FROM_EMAIL, [settings.EMAIL_HOST_USER])

@shared_task
def cleanup_old_rates():
  ten_mins_ago = timezone.now() - timezone.timedelta(minutes=10)
  ExchangeRate.objects.filter(effective_from__lt=ten_mins_ago).delete()