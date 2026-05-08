from django.db.models import QuerySet
from wallets.models import Wallet

class WalletSelector:
  @staticmethod
  def get_wallet_with_limits(user_id, currency) -> Wallet:
    return Wallet.objects.select_related('limit').get(user_id=user_id, currency=currency.lower())

  @staticmethod
  def get_user_wallets(user_id) -> QuerySet:
    return Wallet.objects.filter(user_id=user_id)

  @staticmethod
  def get_frozen_wallets() -> QuerySet:
    return Wallet.objects.filter(status__in=['frozen', 'suspended'])