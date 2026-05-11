from transactions.models import Transaction
from rest_framework.exceptions import NotFound, ValidationError
from refunds.models import Refund
from django.db import transaction as db_transaction
import uuid
from django.utils import timezone

class RefundService:
  @staticmethod
  def _find_original_transaction(tx_id):
    shards = ['default', 'transaction_2026_05', 'transaction_2026_06'] 
    for shard in shards:
      try:
        return Transaction.objects.using(shard).get(id=tx_id)
      except Transaction.DoesNotExist:
        continue
    return None

  @classmethod
  def create_refund_request(cls, transaction_id, amount, reason, user_id):
    original_tx = cls._find_original_transaction(transaction_id)
    if not original_tx:
      raise NotFound('the orig trans not pres in any shard.')
    if original_tx.status != 'completed':
      raise ValidationError(f'only the comple. trans can be refun. status {original_tx.status}')
    if amount > original_tx.amount:
      raise ValidationError('the refund amount cant exc orig trans amount.')
    if Refund.objects.filter(original_transaction_id=transaction_id).exclude(status = 'rejected').exists():
      raise ValidationError('the refund request alr for this trans')

    refund_request = Refund.objects.create(original_transaction_id=transaction_id, amount=amount, reason=reason,
      requested_by=user_id, status = 'requested')
        
    return refund_request

  @classmethod
  def approve_refund(cls, refund_id, admin_id):
    refund = Refund.objects.get(id=refund_id)
    if refund.status != 'requested':
      raise ValidationError(f'cant approve. the curr status is {refund.status}')
    original_tx = cls._find_original_transaction(refund.original_transaction_id)
    if not original_tx:
      raise NotFound('the orig trans is not pres.')

    with db_transaction.atomic():
      refund_tx = Transaction.objects.create(from_wallet_id=original_tx.to_wallet_id, to_wallet_id=original_tx.from_wallet_id,
        amount=refund.amount, currency=original_tx.currency, status = 'initiated', transaction_type = 'refund',
          idempotency_key=f'REFUND-{refund.id}-{uuid.uuid4().hex[:8]}')
      refund.status = 'approved'
      refund.approved_by = admin_id
      refund.refund_transaction = refund_tx.id
      refund.save()
    return refund

  @classmethod
  def process_refund(cls, refund_id):
    refund = Refund.objects.get(id=refund_id)
    if refund.status != 'approved':
      raise ValidationError('only the appro refs can be proces.') 
    refund.status = 'completed'
    if refund.refund_transaction:
      tx = cls._find_original_transaction(refund.refund_transaction)
      if tx:
        tx.status = 'completed'
        tx.completed_at = timezone.now()
        tx.save(using=tx._state.db) 
      else:
        raise NotFound('the linked refund trans isnt pres in any shard.')
    refund.save()
    return refund