from django.dispatch import receiver
from django.db.models.signals import post_save
from wallets.models import Wallet, WalletLimit

@receiver(post_save, sender=Wallet)
def create_wallet_limit(sender, instance, created, **kwargs):
  if created:
    WalletLimit.objects.get_or_create(wallet=instance, defaults={'tier': 'tier1', 'daily_limit': 20000.00, 'monthly_limit': 5000000.00,
      'transaction_limit': 10000.00})