from decimal import Decimal
from django.utils import timezone
from limits.models import DailySpending, MonthlySpending, FraudFlag
from django.db.models import F
from datetime import timedelta
from django.db.models import Avg

class LimitCheckService:
  @staticmethod
  def check_daily_limit(wallet, amount):
    limit_config = wallet.limit 
    usage, _ = DailySpending.objects.get_or_create(wallet=wallet, date=timezone.now().date())
    return (usage.total_spent + Decimal(amount)) <= limit_config.daily_limit

  @staticmethod
  def check_monthly_limit(wallet, amount):
    limit_config = wallet.limit
    now = timezone.now()
    usage, _ = MonthlySpending.objects.get_or_create(wallet=wallet, year=now.year, month=now.month)
    return (usage.total_spent + Decimal(amount)) <= limit_config.monthly_limit

  @staticmethod
  def check_transaction_limit(wallet, amount):
    limit_config = wallet.limit
    return Decimal(amount) <= limit_config.transaction_limit

  @classmethod
  def check_all_limits(cls, wallet, amount):
    if not cls.check_transaction_limit(wallet, amount):
      return False, 'the transaction exceeds single limit.'     
    if not cls.check_daily_limit(wallet, amount):
      return False, 'the daily spen limit is rea.'    
    if not cls.check_monthly_limit(wallet, amount):
      return False, 'the mon spen limit is rea.'   
    return True, 'the limits are cleared.'
  
  @staticmethod
  def update_spending_totals(wallet, amount):
    today = timezone.now().date()
    now = timezone.now()
    decimal_amount = Decimal(amount)
    
    for model, lookup in [(DailySpending, {'wallet': wallet, 'date': today}),
      (MonthlySpending, {'wallet': wallet, 'year': now.year, 'month': now.month})]:
      
      obj, created = model.objects.get_or_create(**lookup)
      if created:
        obj.total_spent = decimal_amount
        obj.transaction_count = 1
        obj.save()
      else:
        model.objects.filter(pk=obj.pk).update(total_spent=F('total_spent') + decimal_amount, transaction_count=F('transaction_count') + 1)

class FraudDetectionService:
  @staticmethod
  def detect_rapid_transactions(wallet):
    five_mins_ago = timezone.now() - timedelta(minutes=5)
    count = wallet.record.filter(created_at__gte=five_mins_ago).count()  
    if count > 10:
      FraudFlag.objects.create(wallet=wallet, reason = 'rapid', metadata = {'count': count, 'window': '5m'})
      return True
    return False

  @staticmethod
  def detect_unusual_amount(wallet, amount):
    avg_data = wallet.record.all().order_by('-created_at')[:20].aggregate(Avg('amount'))
    avg_val = avg_data['amount__avg']
    if avg_val and Decimal(amount) > (avg_val * 5):
      FraudFlag.objects.create(wallet=wallet, reason = 'large', metadata = {'amount': str(amount), 'avg': str(avg_val)})
      return True
    return False

  @staticmethod
  def detect_unusual_time(wallet):
    current_hour = timezone.now().hour
    if 2 <= current_hour <= 5:
      FraudFlag.objects.create(wallet=wallet, reason = 'unusual', metadata = {'hour': current_hour, 'context': 'Late night transaction'})
      return True
    return False