from django.conf import settings
from django.utils import timezone

def get_transaction_shard(timestamp=None):
  if timestamp is None:
    timestamp = timezone.now()
  formatted_date = timestamp.strftime('%Y_%m')
  shard_name = f'transaction_{formatted_date}'
    
  if shard_name in settings.DATABASES:
    return shard_name
  current_month = timezone.now().strftime('%Y_%m')
  current_shard = f'transaction_{current_month}'
    
  if current_shard in settings.DATABASES:
    return current_shard
  return 'default'