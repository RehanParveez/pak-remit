from django.db import transaction
from wallets.models import Wallet, WalletLimit, WalletBookings, WalletRecord
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum

class WalletService:
  @staticmethod
  def create_wallet(user_id, currency = 'pkr'):
    with transaction.atomic():
      wallet = Wallet.objects.create(user_id=user_id, currency=currency.lower(), balance=Decimal('0.00'),
        reserved_balance=Decimal('0.00'), available_balance=Decimal('0.00'))
      WalletLimit.objects.create(wallet=wallet)
      return wallet
  
  @staticmethod
  def deposit_funds(wallet_id, amount, description = 'Deposit'):
    amount = Decimal(str(amount))
    with transaction.atomic():
      wallet = Wallet.objects.select_for_update().get(id=wallet_id)
      wallet.balance += amount
      wallet.save() 
      WalletRecord.objects.create(wallet=wallet, amount=amount, type = 'credit', description=description)
      return wallet

  @staticmethod
  def reserve_funds(wallet_id, amount, reason, timeout_minutes=30):
    amount = Decimal(str(amount))
    with transaction.atomic():
      wallet = Wallet.objects.select_for_update().get(id=wallet_id)
            
      if wallet.available_balance < amount:
        raise ValueError('avail bal is not enough.')
      wallet.reserved_balance += amount
      wallet.save()
      booking = WalletBookings.objects.create(wallet=wallet, amount=amount, reason=reason,
        expires_at=timezone.now() + timezone.timedelta(minutes=timeout_minutes))
      return booking
  
  @staticmethod
  def commit_funds(booking_id):
    with transaction.atomic():
      booking = WalletBookings.objects.select_for_update().get(id=booking_id) 
      if booking.is_committed or booking.is_released:
        raise ValueError('the booking is alr proces.')
      wallet = booking.wallet
      wallet.balance -= booking.amount
      wallet.reserved_balance -= booking.amount
      wallet.save() 

      WalletRecord.objects.create(wallet=wallet, amount=booking.amount, type = 'debit', description = f'payment for {booking.reason}')
      booking.is_committed = True
      booking.save()  
      return True
  
  @staticmethod
  def release_funds(booking_id):
    with transaction.atomic():
      booking = WalletBookings.objects.select_for_update().get(id=booking_id)
      if booking.is_committed or booking.is_released:
        return False
      wallet = booking.wallet
      wallet.reserved_balance -= booking.amount
      wallet.save()
      booking.is_released = True
      booking.save()
            
      return True
  
  @staticmethod
  def check_sufficient_balance(wallet_id, amount) -> bool:
    wallet = Wallet.objects.get(id=wallet_id)
    return wallet.available_balance >= Decimal(str(amount))

  @staticmethod
  def upgrade_tier(wallet_id, new_tier):
    with transaction.atomic():
      wallet = Wallet.objects.select_related('limit').get(id=wallet_id)
      limit = wallet.limit  
      if new_tier == 'tier1':
        limit.daily_limit = Decimal('20000.00')
        limit.transaction_limit = Decimal('10000.00')
      elif new_tier == 'tier2':
        limit.daily_limit = Decimal('100000.00')
        limit.transaction_limit = Decimal('50000.00')
      elif new_tier == 'tier3':
        limit.daily_limit = Decimal('1000000.00')
        limit.transaction_limit = Decimal('500000.00')
     
      limit.tier = new_tier
      limit.save()
      return limit
  
class BalanceService:
  @staticmethod
  def calculate_balance(wallet_id):
    credits = WalletRecord.objects.filter(wallet_id=wallet_id, type='credit').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    debits = WalletRecord.objects.filter(wallet_id=wallet_id, type = 'debit').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    return credits - debits