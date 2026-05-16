from celery import shared_task
from transactions.services import shard_context
from transactions.models import Transaction
# from urllib.parse import urljoin
import requests
import time
from django.utils import timezone
from celery import current_app
from django.conf import settings
from parent.circuit_utils import breaker_call, WALLET_BREAKER
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_transaction_async(transaction_id):
  with shard_context():
    txn = Transaction.objects.filter(id=transaction_id).first()
    if not txn:
      return f'Transaction {transaction_id} not found.'
    txn.status = 'validating'
    txn.save(update_fields=['status'])
    url_reserve = f'{settings.WALLET_SERVICE_URL}/wallets/wallet/reserve/'
    headers = {'X-Internal-Token': settings.INTERNAL_SERVICE_SECRET}
    payload = {'wallet_id': str(txn.from_wallet_id), 'amount': str(txn.amount), 'transaction_id': str(txn.id)}
    response, error = breaker_call(WALLET_BREAKER, requests.post, url_reserve, json=payload, headers=headers, timeout=10)
    if error:
      logger.error('wallet reserve circuit open for txn %s: %s', transaction_id, error)
      txn.status = 'failed'
      txn.save(update_fields=['status'])
      return 'Failed at reservation, the wallet serv is unavail.'
    if response.status_code != 200:
      txn.status = 'failed'
      txn.save(update_fields=['status'])
      return 'Failed at reservation.'

    txn.status = 'processing'
    txn.save(update_fields=['status'])
    time.sleep(2) 
    url_settle = f'{settings.WALLET_SERVICE_URL}/wallets/wallet/settle/'
    settle_response, error = breaker_call(WALLET_BREAKER, requests.post, url_settle, json={'transaction_id': str(txn.id)}, headers=headers, timeout=10)
    if error:
      logger.error('wallet settle circuit open for txn %s: %s', transaction_id, error)
      txn.status = 'failed'
      txn.save(update_fields=['status'])
      return 'Failed at settlement, the wallet serv is unavail.'
    if settle_response.status_code != 200:
      txn.status = 'failed'
      txn.save(update_fields=['status'])
      return 'Failed at settlement.'
    txn.status = 'completed'
    txn.completed_at = timezone.now()
    txn.save(update_fields=['status', 'completed_at'])
    # from transactions.tasks import send_transaction_email # impor this here due to circular impor issue
    current_app.send_task('emails.tasks.send_transaction_notification', args=[str(txn.id), 'rehanrural@gmail.com', 'rehanrural@gmail.com'], queue = 'notifications')
    current_app.send_task('webhooks.tasks.trigger_transaction_webhook', args=[str(txn.id), str(txn.to_wallet_id)], queue = 'notifications')
    return f'the transa {txn.id} is finished.'

@shared_task
def send_transaction_email(transaction_id, sender_email=None, receiver_email=None):
  pass
  with shard_context():
    txn = Transaction.objects.filter(id=transaction_id).first()
    if not txn:
      return f'transaction {transaction_id} not pres.'
    if txn.status != 'completed':
      return f'transaction {transaction_id} is in {txn.status} state.'
    sen_email = sender_email or 'rehanrural@gmail.com'
    rec_email = receiver_email or 'rehanrural@gmail.com'
    current_app.send_task('emails.tasks.send_transaction_notification', args=[str(txn.id), sen_email, rec_email], queue = 'notifications')
    return f'notifi for Txn {txn.id} to redis.'

@shared_task
def retry_failed_transactions():
  five_mins_ago = timezone.now() - timezone.timedelta(minutes=5)
  with shard_context():
    stuck_list = Transaction.objects.filter(status = 'processing', created_at__lt=five_mins_ago)
    for txn in stuck_list:
      process_transaction_async.delay(txn.id)

@shared_task
def cleanup_old_transactions():
  print('running the mont archive task')