from rest_framework import permissions
from django.conf import settings
import requests
from django.utils import timezone
from datetime import timedelta
from parent.circuit_utils import breaker_call, WALLET_BREAKER
import logging

logger = logging.getLogger(__name__)

class EnoughBalancePerm(permissions.BasePermission):
  def has_permission(self, request, view):
    wallet_id = request.data.get('from_wallet_id')
    if not wallet_id:
      wallet_id = request.data.get('wallet_id')
    amount = request.data.get('amount')
    if not wallet_id:
      return False
            
    if not amount:
      return False
    url = f'{settings.WALLET_SERVICE_URL}/wallets/wallet/check-balance/'
    headers = {'X-Internal-Token': settings.INTERNAL_SERVICE_SECRET, 'Content-Type': 'application/json'}
    payload = {'wallet_id': str(wallet_id), 'amount': str(amount)}
    response, error = breaker_call(WALLET_BREAKER, requests.post, url, json=payload, headers=headers, timeout=5)
    if error:
      logger.error('wallet balance check circuit open: %s', error)
      return False
    if response.status_code == 200:
      return True
    return False

class RefundPermission(permissions.BasePermission):
  def has_object_permission(self, request, view, obj):
    if obj.status != 'completed':
      return False
    if not obj.completed_at:
      return False   
    now = timezone.now()
    thirty_days = timedelta(days=30)
    time_limit = now - thirty_days

    if obj.completed_at < time_limit:
      return False
    return True