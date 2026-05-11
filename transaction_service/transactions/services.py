from django.core.cache import caches
from contextlib import contextmanager
from transactions.utils import get_transaction_shard
from parent.sharding_utils import set_current_shard, clear_current_shard
from django.utils import timezone
import json
from decimal import Decimal
from django.conf import settings
import requests
from django.db import transaction
from transactions.models import Transaction, TransactionFee, TransactionMetadata

cache = caches['default']

@contextmanager
def shard_context(timestamp=None):
  shard = get_transaction_shard(timestamp)
  set_current_shard(shard)
  try:
    yield shard
  finally:
    clear_current_shard()

class StateMachine:
  VALID_TRANSITIONS = {'initiated': ['validating', 'failed'], 'validating': ['processing', 'failed'],
    'processing': ['clearing', 'failed'], 'clearing': ['settled', 'failed'], 'settled': ['completed', 'failed'],
    'completed': ['refunded'], 'failed': [], 'refunded': []}
    
  @classmethod
  def transition(cls, transaction_obj, new_status):
    current_status = transaction_obj.status
    if new_status not in cls.VALID_TRANSITIONS.get(current_status, []):
      raise ValueError(f'illegal transition: {current_status} -> {new_status}. '
      f'Allowed: {cls.VALID_TRANSITIONS.get(current_status, [])}')
    transaction_obj.status = new_status
    update_fields = ['status', 'updated_at']
        
    if new_status == 'settled':
      transaction_obj.settled_at = timezone.now()
      update_fields.append('settled_at')
    elif new_status == 'completed':
      transaction_obj.completed_at = timezone.now()
      update_fields.append('completed_at')  
    transaction_obj.save(update_fields=update_fields)
    return transaction_obj

class IdempotencyService:
  CACHE_TIMEOUT = 86400  
    
  @staticmethod
  def get_key(idempotency_key):
    return f'idempotency:{idempotency_key}'
    
  @classmethod
  def check_duplicate(cls, idempotency_key):
    cached_data = cache.get(cls.get_key(idempotency_key))
    return json.loads(cached_data) if cached_data else None
    
  @classmethod
  def cache_response(cls, idempotency_key, response_data):
    cache.set(cls.get_key(idempotency_key), json.dumps(response_data), timeout=cls.CACHE_TIMEOUT)

class TransactionService:
  FEE_RATES = {'merchant': Decimal('0.015'), 'p2p': Decimal('0.00'), 'remittance': Decimal('0.005'), 'bill': Decimal('0.01'), 'refund': Decimal('0.00')}
    
  @staticmethod
  def _get_internal_headers():
    return {'X-Internal-Token': settings.INTERNAL_SERVICE_SECRET, 'Content-Type': 'application/json'}
    
  @classmethod
  def _call_wallet_service(cls, endpoint, payload):
    url = f'http://127.0.0.1:8001/wallets/wallet/{endpoint}/'  
    response = requests.post(url, json=payload, headers=cls._get_internal_headers(), timeout=5)
    if response.status_code != 200:
      raise ValueError(f'the wallet service err: {response.text}')
    return response.json()
    
  @classmethod
  def _calculate_fee(cls, amount, txn_type):
    rate = cls.FEE_RATES.get(txn_type, Decimal('0.00'))
    percentage_fee = rate * Decimal('100')
    total_fee = amount * rate
    return percentage_fee, total_fee
    
  @classmethod
  def _validate_transaction_data(cls, from_wallet_id, to_wallet_id, amount, txn_type):
    amount = Decimal(str(amount))
    if from_wallet_id == to_wallet_id:
      raise ValueError('It cant be transferred to the same wallet')
    if amount <= 0:
      raise ValueError('the amount s/h be greater than zero')
    if txn_type not in cls.FEE_RATES:
      raise ValueError(f'wrong transa type: {txn_type}')
    
  @classmethod
  def initiate_transaction(cls, from_wallet_id, to_wallet_id, amount, currency, idempotency_key, txn_type, metadata=None):
    amount = Decimal(str(amount))
    cls._validate_transaction_data(from_wallet_id, to_wallet_id, amount, txn_type)
    with shard_context():
      with transaction.atomic():
        txn = Transaction.objects.create(from_wallet_id=from_wallet_id, to_wallet_id=to_wallet_id, amount=amount,
        currency=currency.lower(), transaction_type=txn_type, idempotency_key=idempotency_key, status = 'initiated')
        percentage_fee, total_fee = cls._calculate_fee(amount, txn_type)
        TransactionFee.objects.create(transaction=txn, base_fee=Decimal('0.00'), percentage_fee=percentage_fee, total_fee=total_fee, currency=txn.currency)
        if metadata:
          TransactionMetadata.objects.create(transaction=txn, **metadata)
        return txn
    
  @classmethod
  def validate_transaction(cls, transaction_id):
    txn = Transaction.objects.select_for_update().get(id=transaction_id)
    with shard_context(txn.created_at):
      with transaction.atomic():
        try:
          cls._call_wallet_service('check-balance', {'wallet_id': str(txn.from_wallet_id), 'amount': str(txn.amount)})
        except (requests.RequestException, ValueError) as e:
          StateMachine.transition(txn, 'failed')
          raise ValueError(f'the valida. failed: {str(e)}')
        return StateMachine.transition(txn, 'validating')
    
  @classmethod
  def process_transaction(cls, transaction_id):
    txn = Transaction.objects.select_for_update().get(id=transaction_id)
    with shard_context(txn.created_at):
      with transaction.atomic():
        try:
          booking_data = cls._call_wallet_service('reserve', {'wallet_id': str(txn.from_wallet_id), 'amount': str(txn.amount),
            'reason': f'Transaction {txn.id}', 'timeout_minutes': 30})             
          metadata, _ = TransactionMetadata.objects.get_or_create(transaction=txn)
          metadata.external_ref = booking_data.get('booking_id')
          metadata.save()
                     
        except (requests.RequestException, ValueError) as e:
          StateMachine.transition(txn, 'failed')
          raise ValueError(f'Processing failed: {str(e)}')
        return StateMachine.transition(txn, 'processing')
    
  @classmethod
  def settle_transaction(cls, transaction_id):
    txn = Transaction.objects.select_for_update().get(id=transaction_id) 
    with shard_context(txn.created_at):
      with transaction.atomic():
        try:
          booking_id = txn.metadata.external_ref
        except TransactionMetadata.DoesNotExist:
          StateMachine.transition(txn, 'failed')
          raise ValueError("Missing booking reference")
                
        try:
          cls._call_wallet_service('commit', {'booking_id': booking_id})
        except (requests.RequestException, ValueError) as e:
          StateMachine.transition(txn, 'failed')
          raise ValueError(f"Settlement failed: {str(e)}")  
        return StateMachine.transition(txn, 'settled')
    
  @classmethod
  def complete_transaction(cls, transaction_id):
    txn = Transaction.objects.select_for_update().get(id=transaction_id)  
    with shard_context(txn.created_at):
      with transaction.atomic():
        return StateMachine.transition(txn, 'completed')