from rest_framework.test import APIRequestFactory, APITestCase 
from rest_framework.views import APIView
from unittest.mock import patch, MagicMock
from transactions.permissions import EnoughBalancePerm, RefundPermission
from rest_framework.request import Request
from rest_framework.parsers import JSONParser
from django.utils import timezone
from datetime import timedelta

factory = APIRequestFactory()
view = APIView()

def make_obj(**kwargs):
  class Obj:
    pass
  o = Obj()
  for k, v in kwargs.items():
    setattr(o, k, v)
  return o

def mock_response(status_code):
  r = MagicMock()
  r.status_code = status_code
  return r

class EnoughBalancePerm_Tests(APITestCase):
  def setUp(self):
    self.perm = EnoughBalancePerm()

  def _post(self, data):
    request = factory.post('/transactions/transaction/p2p/', data=data, format='json')
    drf_request = Request(request, parsers=[JSONParser()])
    return drf_request

  def test_denies_when_from_wallet_id_missing(self):
    request = self._post({'amount': '1000'})
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_when_wallet_id_missing(self):
    request = self._post({'to_wallet_id': 'some-id', 'amount': '1000'})
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_when_amount_missing(self):
    request = self._post({'from_wallet_id': 'wallet-uuid'})
    self.assertFalse(self.perm.has_permission(request, view))

  def test_accepts_wallet_id_as_fallback(self):
    request = self._post({'wallet_id': 'wallet-uuid', 'amount': '500'})
    with patch('transactions.permissions.breaker_call') as mock_bc:
      mock_bc.return_value = (mock_response(200), None)
      self.assertTrue(self.perm.has_permission(request, view))

  def test_allows_when_wallet_service_returns_200(self):
    request = self._post({'from_wallet_id': 'wallet-uuid', 'amount': '1000'})
    with patch('transactions.permissions.breaker_call') as mock_bc:
      mock_bc.return_value = (mock_response(200), None)
      self.assertTrue(self.perm.has_permission(request, view))

  def test_denies_when_wallet_service_returns_400(self):
    request = self._post({'from_wallet_id': 'wallet-uuid', 'amount': '9500000'})
    with patch('transactions.permissions.breaker_call') as mock_bc:
      mock_bc.return_value = (mock_response(400), None)
      self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_when_wallet_service_returns_500(self):
    request = self._post({'from_wallet_id': 'wallet-uuid', 'amount': '100'})
    with patch('transactions.permissions.breaker_call') as mock_bc:
      mock_bc.return_value = (mock_response(500), None)
      self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_when_circuit_breaker_open(self):
    request = self._post({'from_wallet_id': 'wallet-uuid', 'amount': '100'})
    with patch('transactions.permissions.breaker_call') as mock_bc:
      mock_bc.return_value = (None, 'Circuit breaker is OPEN')
      self.assertFalse(self.perm.has_permission(request, view))

  def test_logs_error_when_circuit_breaker_open(self):
    request = self._post({'from_wallet_id': 'wallet-uuid', 'amount': '100'})
    with patch('transactions.permissions.breaker_call') as mock_bc:
      mock_bc.return_value = (None, 'Circuit breaker is OPEN')
      with self.assertLogs('transactions.permissions', level = 'ERROR'):
        self.perm.has_permission(request, view)

  def test_payload_values_are_stringified(self):
    request = self._post({'from_wallet_id': 'wallt-023', 'amount': 750})
    with patch('transactions.permissions.breaker_call') as mock_bc:
      mock_bc.return_value = (mock_response(200), None)
      self.perm.has_permission(request, view)
      call_kwargs = mock_bc.call_args[1]
      payload = call_kwargs.get('json')
      self.assertEqual(payload['wallet_id'], 'wallt-023')
      self.assertEqual(payload['amount'], '750')

class RefundPermission_Tests(APITestCase):

  def setUp(self):
    self.perm = RefundPermission()

  def _req(self):
    request = factory.post('/transactions/transaction/refund/')
    return Request(request, parsers=[JSONParser()])

  def _tx(self, status = 'completed', days_ago=None, completed_at=None):
    if completed_at is None and days_ago is not None:
      completed_at = timezone.now() - timedelta(days=days_ago)
    return make_obj(status=status, completed_at=completed_at)

  def test_allows_refund_completed_1_day_ago(self):
    self.assertTrue(self.perm.has_object_permission(self._req(), view, self._tx(days_ago=1)))

  def test_allows_refund_completed_29_days_ago(self):
    self.assertTrue(self.perm.has_object_permission(self._req(), view, self._tx(days_ago=29)))

  def test_denies_refund_completed_31_days_ago(self):
    self.assertFalse(self.perm.has_object_permission(self._req(), view, self._tx(days_ago=31)))

  def test_denies_refund_completed_365_days_ago(self):
    self.assertFalse(self.perm.has_object_permission(self._req(), view, self._tx(days_ago=365)))

  def test_denies_pending_transaction(self):
    self.assertFalse(self.perm.has_object_permission(self._req(), view, self._tx(status = 'pending', days_ago=1)))

  def test_denies_processing_transaction(self):
    self.assertFalse(self.perm.has_object_permission(self._req(), view, self._tx(status = 'processing', days_ago=1)))

  def test_denies_failed_transaction(self):
    self.assertFalse(self.perm.has_object_permission(self._req(), view, self._tx(status = 'failed', days_ago=1)))

  def test_denies_already_refunded_transaction(self):
    self.assertFalse(self.perm.has_object_permission(self._req(), view, self._tx(status = 'refunded', days_ago=1)))

  def test_denies_completed_with_no_timestamp(self):
    self.assertFalse(self.perm.has_object_permission(self._req(), view, self._tx(status = 'completed', completed_at=None)))

  def test_boundary_just_inside_30_days(self):
    just_inside = timezone.now() - timedelta(days=30) + timedelta(seconds=1)
    obj = make_obj(status = 'completed', completed_at=just_inside)
    self.assertTrue(self.perm.has_object_permission(self._req(), view, obj))