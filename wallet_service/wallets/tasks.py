from celery import shared_task
from django.utils import timezone
from wallets.models import WalletBookings, WalletRecord, Wallet
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum

SHARDS = ['shard_1', 'shard_2']

@shared_task
def release_expired_bookings():
  now = timezone.now()
  for db in SHARDS:
    expired_bookings = WalletBookings.objects.using(db).filter(expires_at__lt=now, is_released=False, is_committed=False)
    for booking in expired_bookings:
      with transaction.atomic(using=db):
        wallet = booking.wallet
        wallet.reserved_balance -= booking.amount
        wallet.save() 
        booking.is_released = True
        booking.save()
        WalletRecord.objects.create(wallet=wallet, amount=booking.amount, type = 'credit', description = f'relea: {booking.reason}')
        send_mail('Funds Unlocked', f'booking of {booking.amount} {wallet.currency} has expired and is now avail.',
          settings.DEFAULT_FROM_EMAIL, [f'user_{wallet.user_id}@practice.com'], fail_silently=True)

@shared_task
def calculate_daily_spending():
  today = timezone.now().date()
  for db in SHARDS:
    wallets = Wallet.objects.using(db).all()  
    for wallet in wallets:
      total_spent = WalletRecord.objects.using(db).filter(wallet=wallet, type = 'debit', created_at__date=today).aggregate(total=Sum('amount'))['total'] or 0  
      limit_obj = wallet.limit
      limit_obj.daily_spent = total_spent
      limit_obj.save(using=db)  
      send_mail('Daily Spending Summary', f'Total spent today ({today}): {total_spent} {wallet.currency}. your limit is {limit_obj.daily_limit}.',
        settings.DEFAULT_FROM_EMAIL, [f'user_{wallet.user_id}@practice.com'], fail_silently=True)