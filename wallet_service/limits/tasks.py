from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from wallets.models import WalletRecord, Wallet
from limits.services import FraudDetectionService
from django.core.mail import send_mail
from django.conf import settings

@shared_task()
def run_fraud_detection():
  now = timezone.now()
  last_hour = now - timedelta(hours=1)
  alerts_found = []
  all_shards = [db for db in settings.DATABASES if db != 'default']
    
  for db_name in all_shards:
    active_ids = WalletRecord.objects.using(db_name).filter(created_at__gte=last_hour).values_list('wallet_id', flat=True).distinct()
    for w_id in active_ids:
      wallet_obj = Wallet.objects.using(db_name).get(id=w_id)
      is_rapid = FraudDetectionService.detect_rapid_transactions(wallet_obj)
      is_unusual = FraudDetectionService.detect_unusual_time(wallet_obj)
            
      if is_rapid or is_unusual:
        alerts_found.append(f'Shard {db_name}: User {wallet_obj.user_id}')

  if alerts_found:
    send_mail('fraud detec alert', f'doubtful activity in {alerts_found}', settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL], fail_silently=False)
  return f'found {len(alerts_found)} doubtful wallets.'