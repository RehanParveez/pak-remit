from rest_framework.test import APITestCase, APIRequestFactory
from django.test import RequestFactory
from django.http import HttpResponse
from wallets.middleware import ShardRoutingMiddleware
from django.contrib.auth.models import AnonymousUser, User
import json
import threading
from parent.sharding_utils import clear_current_shard, get_shard_for_user, get_current_shard, set_current_shard
import time
from rest_framework.views import APIView
from django.conf import settings
from wallets.permissions import InternalServiceGuard, WalletAccessPermission
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

VALID_SHARDS = ['shard_1', 'shard_2']

class ShardRoutingMiddlewareSetup(APITestCase):
  @classmethod
  def setUpTestData(cls):
    cls.verified_user = User.objects.create_user(username = 'verified_user', password = 'user112312')
    cls.merchant = User.objects.create_user(username = 'merchant', password = 'mer12312')
    cls.admin = User.objects.create_user(username = 'admin', password = 'admin123', is_staff=True)

  def setUp(self):
    super().setUp()
    self.factory = RequestFactory()

  def tearDown(self):
    clear_current_shard()
    super().tearDown()

  def _make_capturing_middleware(self, captured: dict):
        
    def capturing_view(request):
      captured['shard'] = get_current_shard()
      return HttpResponse('ok')
    return ShardRoutingMiddleware(get_response=capturing_view)

  def _simple_middleware(self):
    return ShardRoutingMiddleware(get_response=lambda r: HttpResponse('ok'))

class ShardRoutingMiddleware_AuthenticatedUserTests(ShardRoutingMiddlewareSetup):

  def test_sets_shard_for_authenticated_user(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    request = self.factory.get('/wallets/wallet/')
    request.user = self.verified_user
    mw(request)
    self.assertIsNotNone(captured.get('shard'))
    self.assertIn(captured['shard'], VALID_SHARDS)

  def test_shard_cleared_after_request_completes(self):
    mw = self._simple_middleware()
    request = self.factory.get('/wallets/wallet/')
    request.user = self.verified_user
    mw(request)
    self.assertIsNone(get_current_shard())

  def test_same_user_always_routes_to_same_shard(self):
    shard_a = get_shard_for_user(self.verified_user.pk)
    shard_b = get_shard_for_user(self.verified_user.pk)
    self.assertEqual(shard_a, shard_b)

  def test_merchant_user_routes_to_a_valid_shard(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    request = self.factory.get('/wallets/wallet/')
    request.user = self.merchant
    mw(request)
    self.assertIn(captured.get('shard'), VALID_SHARDS)

  def test_admin_user_routes_to_a_valid_shard(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    request = self.factory.get('/wallets/wallet/')
    request.user = self.admin
    mw(request)
    self.assertIn(captured.get('shard'), VALID_SHARDS)

class ShardRoutingMiddleware_AnonymousUserTests(ShardRoutingMiddlewareSetup):

  def test_no_shard_set_for_anonymous_user_on_regular_path(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    request = self.factory.get('/wallets/wallet/')
    request.user = AnonymousUser()
    mw(request)
    self.assertIsNone(captured.get('shard'))

  def test_does_not_crash_for_anonymous_user(self):
    mw = self._simple_middleware()
    request = self.factory.get('/wallets/wallet/')
    request.user = AnonymousUser()
    try:
      response = mw(request)
    except Exception as exc:
      self.fail(f'the middleware stopped for the AnonymousUser: {exc}')
    self.assertEqual(response.status_code, 200)

class ShardRoutingMiddleware_InternalPathTests(ShardRoutingMiddlewareSetup):

  def _post_with_user_id(self, path, user_id=None):
    uid = user_id or str(self.verified_user.pk)
    body = json.dumps({'user_id': uid, 'currency': 'PKR'})
    request = self.factory.post(path, data=body, content_type='application/json')
    request.user = AnonymousUser()
    return request

  def test_create_internal_path_reads_user_id_from_body(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    request = self._post_with_user_id('/wallets/wallet/create-internal/')
    mw(request)
    self.assertIsNotNone(captured.get('shard'))
    self.assertIn(captured['shard'], VALID_SHARDS)

  def test_check_balance_path_reads_user_id_from_body(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    request = self._post_with_user_id('/wallets/wallet/check-balance/')
    mw(request)
    self.assertIn(captured.get('shard'), VALID_SHARDS)

  def test_reserve_path_reads_user_id_from_body(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    request = self._post_with_user_id('/wallets/wallet/reserve/')
    mw(request)
    self.assertIn(captured.get('shard'), VALID_SHARDS)

  def test_settle_path_reads_user_id_from_body(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    request = self._post_with_user_id('/wallets/wallet/settle/')
    mw(request)
    self.assertIn(captured.get('shard'), VALID_SHARDS)

  def test_upgrade_tier_path_reads_user_id_from_body(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    request = self._post_with_user_id('/wallets/wallet/upgrade-tier/')
    mw(request)
    self.assertIn(captured.get('shard'), VALID_SHARDS)

  def test_internal_path_body_shard_matches_direct_call(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    uid = str(self.verified_user.pk)
    body = json.dumps({'user_id': uid})
    request = self.factory.post('/wallets/wallet/create-internal/', data=body, content_type='application/json')
    request.user = AnonymousUser()
    mw(request)
    expected_shard = get_shard_for_user(uid)
    self.assertEqual(captured.get('shard'), expected_shard)

  def test_get_on_internal_path_falls_back_to_request_user(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    request = self.factory.get('/wallets/wallet/create-internal/')
    request.user = self.verified_user
    mw(request)
    self.assertIn(captured.get('shard'), VALID_SHARDS)

  def test_regular_path_post_with_user_id_in_body_ignored(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    body = json.dumps({'user_id': str(self.verified_user.pk)})
    request = self.factory.post('/wallets/wallet/', data=body, content_type='application/json')
    request.user = AnonymousUser()
    mw(request)
    self.assertIsNone(captured.get('shard'))

class ShardRoutingMiddleware_EdgeCaseTests(ShardRoutingMiddlewareSetup):

  def test_malformed_json_body_does_not_crash(self):
    mw = self._simple_middleware()
    request = self.factory.post('/wallets/wallet/create-internal/', data = 'this is { not valid json', content_type = 'application/json')
    request.user = AnonymousUser()
    try:
      response = mw(request)
    except json.JSONDecodeError:
      self.fail('the middleware s/h not spread JSONDecodeError')
    self.assertEqual(response.status_code, 200)

  def test_empty_body_does_not_crash(self):
    mw = self._simple_middleware()
    request = self.factory.post('/wallets/wallet/create-internal/', content_type = 'application/json')
    request._body = b''
    request.user = AnonymousUser()
    try:
      response = mw(request)
    except Exception as exc:
      self.fail(f'the middleware stopped on the empty body: {exc}')
    self.assertEqual(response.status_code, 200)

  def test_body_without_user_id_key_does_not_crash(self):
    mw = self._simple_middleware()
    body = json.dumps({'currency': 'PKR', 'amount': '800'})
    request = self.factory.post('/wallets/wallet/create-internal/', data=body, content_type = 'application/json')
    request.user = AnonymousUser()
    try:
      response = mw(request)
    except Exception as exc:
      self.fail(f'the midd stopped when the user_id was miss. from body: {exc}')
    self.assertEqual(response.status_code, 200)

  def test_shard_not_set_when_body_has_no_user_id(self):
    captured = {}
    mw = self._make_capturing_middleware(captured)
    body = json.dumps({'currency': 'PKR'})
    request = self.factory.post('/wallets/wallet/create-internal/', data=body, content_type = 'application/json')
    request.user = AnonymousUser()
    mw(request)
    self.assertIsNone(captured.get('shard'))

  def test_shard_cleared_even_when_view_raises(self):
    def exploding_view(request):
      raise RuntimeError('Boom')
    mw = ShardRoutingMiddleware(get_response=exploding_view)
    request = self.factory.get('/wallets/wallet/')
    request.user = self.verified_user
    try:
      mw(request)
    except RuntimeError:
      pass
    remaining = get_current_shard()
    if remaining is not None:
      clear_current_shard()
      self.fail(f'shard {remaining!r} leaked after the view excep.')

class ShardRoutingMiddleware_ThreadSafetyTests(ShardRoutingMiddlewareSetup):

  def test_concurrent_requests_do_not_share_shards(self):
    results = {}
    barrier = threading.Barrier(2)
    def run(user, key):
      factory = RequestFactory()
      captured = {}

      def capturing_view(req):
        captured['shard'] = get_current_shard()
        return HttpResponse('ok')
      mw = ShardRoutingMiddleware(get_response=capturing_view)
      request = factory.get('/wallets/wallet/')
      request.user = user
      barrier.wait()
      mw(request)
      results[key] = captured.get('shard')

    t1 = threading.Thread(target=run, args=(self.verified_user, 'user1'))
    t2 = threading.Thread(target=run, args=(self.merchant, 'user2'))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    self.assertIn(results.get('user1'), VALID_SHARDS)
    self.assertIn(results.get('user2'), VALID_SHARDS)

  def test_shard_not_visible_across_threads(self):
    shard_seen_by_b = []

    def thread_a():
      set_current_shard('shard_1')

    def thread_b():
      time.sleep(0.05)
      shard_seen_by_b.append(get_current_shard())
    ta = threading.Thread(target=thread_a)
    tb = threading.Thread(target=thread_b)
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    self.assertIsNone(shard_seen_by_b[0], 'the thread B saw a shard set by thread A, so thread local leaked')

factory = APIRequestFactory()
view = APIView()

def make_auth(user_id = 'orign-user-uuid', control = 'user', is_staff=False, is_kyc_verified=True):
  return {'user_id': user_id, 'control': control, 'is_staff': is_staff, 'is_kyc_verified': is_kyc_verified}

def make_obj(**kwargs):
  class Obj:
    pass
  o = Obj()
  for k, v in kwargs.items():
    setattr(o, k, v)
  return o

class WalletInternalServiceGuardTests(APITestCase):

  def setUp(self):
    self.perm = InternalServiceGuard()

  def test_allows_correct_internal_token(self):
    request = factory.post('/wallets/wallet/create-internal/', HTTP_X_INTERNAL_TOKEN=settings.INTERNAL_SERVICE_SECRET)
    self.assertTrue(self.perm.has_permission(request, view))

  def test_denies_wrong_token(self):
    request = factory.post('/wallets/wallet/create-internal/', HTTP_X_INTERNAL_TOKEN = 'wrong_secret')
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_missing_token(self):
    request = factory.post('/wallets/wallet/create-internal/')
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_empty_token(self):
    request = factory.post('/wallets/wallet/create-internal/', HTTP_X_INTERNAL_TOKEN='')
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_record_service_key_header_instead(self):
    request = factory.post('/wallets/wallet/create-internal/', HTTP_X_INTERNAL_SERVICE_KEY=settings.INTERNAL_SERVICE_SECRET)
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_user_jwt_as_internal_token(self):
    user = User.objects.create_user(username = 'user2', password = 'user12312')
    token = str(RefreshToken.for_user(user).access_token)
    request = factory.post('/wallets/wallet/create-internal/', HTTP_X_INTERNAL_TOKEN=token)
    self.assertFalse(self.perm.has_permission(request, view))

class WalletAccessHasPermTests(APITestCase):

  def setUp(self):
    self.perm = WalletAccessPermission()

  def test_denies_when_auth_is_none(self):
    request = factory.get('/wallets/wallet/')
    request.auth = None
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_unverified_user(self):
    request = factory.get('/wallets/wallet/')
    request.auth = make_auth(is_kyc_verified=False, control = 'user')
    self.assertFalse(self.perm.has_permission(request, view))

  def test_allows_verified_user(self):
    request = factory.get('/wallets/wallet/')
    request.auth = make_auth(is_kyc_verified=True, control = 'user')
    self.assertTrue(self.perm.has_permission(request, view))

  def test_allows_verified_merchant(self):
    request = factory.get('/wallets/wallet/')
    request.auth = make_auth(is_kyc_verified=True, control = 'merchant')
    self.assertTrue(self.perm.has_permission(request, view))

  def test_allows_verified_agent(self):
    request = factory.get('/wallets/wallet/')
    request.auth = make_auth(is_kyc_verified=True, control = 'agent')
    self.assertTrue(self.perm.has_permission(request, view))

  def test_allows_admin_without_kyc(self):
    request = factory.get('/wallets/wallet/')
    request.auth = make_auth(is_kyc_verified=False, control = 'admin')
    self.assertTrue(self.perm.has_permission(request, view))

  def test_allows_staff_without_kyc(self):
    request = factory.get('/wallets/wallet/')
    request.auth = make_auth(is_kyc_verified=False, control = 'user', is_staff=True)
    self.assertTrue(self.perm.has_permission(request, view))

  def test_denies_unknown_control(self):
    request = factory.get('/wallets/wallet/')
    request.auth = make_auth(is_kyc_verified=True, control = 'wrong')
    self.assertFalse(self.perm.has_permission(request, view))

class WalletAccessHasObjectPermTests(APITestCase):

  def setUp(self):
    self.perm = WalletAccessPermission()
    self.user_id = '335d3f19-20b7-4952-b96a-5164196fa151'
    self.other_id = '5b016d6f-b278-4566-8833-937207717cc7'

  def test_admin_can_access_any_wallet(self):
    request = factory.get('/wallets/wallet/1/')
    request.auth = make_auth(user_id=self.user_id, control = 'admin')
    obj = make_obj(user_id=self.other_id)
    self.assertTrue(self.perm.has_object_permission(request, view, obj))

  def test_user_can_access_own_wallet(self):
    request = factory.get('/wallets/wallet/1/')
    request.auth = make_auth(user_id=self.user_id, control = 'user')
    obj = make_obj(user_id=self.user_id)
    self.assertTrue(self.perm.has_object_permission(request, view, obj))

  def test_user_cannot_access_other_wallet(self):
    request = factory.get('/wallets/wallet/1/')
    request.auth = make_auth(user_id=self.user_id, control = 'user')
    obj = make_obj(user_id=self.other_id)
    self.assertFalse(self.perm.has_object_permission(request, view, obj))

  def test_denies_when_auth_is_none(self):
    request = factory.get('/wallets/wallet/1/')
    request.auth = None
    obj = make_obj(user_id=self.user_id)
    self.assertFalse(self.perm.has_object_permission(request, view, obj))