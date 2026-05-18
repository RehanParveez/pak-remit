from accounts.models import User, Profile, UserDevice
from django.test import TestCase, override_settings
from accounts.services import AuthService
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
import json
from django.conf import settings
import hmac
import hashlib
from kyc.tests import IdentityServiceTestCase
from rest_framework import status

def make_user(**kwargs):
  defaults = {'username': 'user1', 'email': 'merchant@pakremit.com', 'phone': '03126204567', 'password': 'mer12312', 'control': 'user'}
  defaults.update(kwargs)
  return User.objects.create_user(**defaults)

class AuthServHashCNICTests(TestCase):

  def test_returns_string(self):
    result = AuthService.hash_cnic('31202-9797651-1')
    self.assertIsInstance(result, str)

  def test_returns_64_char_hex(self):
    result = AuthService.hash_cnic('1234567890123')
    self.assertEqual(len(result), 64)

  def test_same_input_same_output(self):
    cnic = '3520112345678'
    self.assertEqual(AuthService.hash_cnic(cnic), AuthService.hash_cnic(cnic))

  def test_different_input_different_output(self):
    self.assertNotEqual(AuthService.hash_cnic('9797979797979'), AuthService.hash_cnic('6767676767676'))

  def test_empty_string_does_not_crash(self):
    try:
      result = AuthService.hash_cnic('')
      self.assertIsInstance(result, str)
    except Exception as exc:
      self.fail(f'hash_cnic crashed on empty string: {exc}')

  def test_uses_salt(self):
    cnic = '3520112345678'
    raw_hash = __import__('hashlib').sha256(cnic.encode()).hexdigest()
    salted_hash = AuthService.hash_cnic(cnic)
    self.assertNotEqual(raw_hash, salted_hash)

  def test_consistent_across_calls(self):
    cnic = '3520112345678'
    results = [AuthService.hash_cnic(cnic) for _ in range(5)]
    self.assertEqual(len(set(results)), 1)

class AuthServRegUserTests(TestCase):

  def _valid_data(self, **overrides):
    data = {'username': 'user2', 'email': 'user2@pakremit.com', 'phone': '03009876543', 'password': 'user212312', 'full_name': 'User2',
      'cnic': '3520112345678', 'control': 'user'}
    data.update(overrides)
    return data

  def test_creates_user(self):
    AuthService.register_user(self._valid_data())
    self.assertTrue(User.objects.filter(email='user2@pakremit.com').exists())

  def test_creates_profile(self):
    user = AuthService.register_user(self._valid_data())
    self.assertTrue(Profile.objects.filter(user=user).exists())

  def test_returns_user_instance(self):
    user = AuthService.register_user(self._valid_data())
    self.assertIsInstance(user, User)

  def test_profile_has_correct_full_name(self):
    user = AuthService.register_user(self._valid_data(full_name = 'rehan parveez'))
    self.assertEqual(user.profile.full_name, 'rehan parveez')

  def test_profile_default_risk_score_is_zero(self):
    user = AuthService.register_user(self._valid_data())
    self.assertEqual(user.profile.risk_score, 0)

  def test_profile_default_risk_level_is_low(self):
    user = AuthService.register_user(self._valid_data())
    self.assertEqual(user.profile.risk_level, 'low')

  def test_profile_is_not_verified_by_default(self):
    user = AuthService.register_user(self._valid_data())
    self.assertFalse(user.profile.is_verified)

  def test_cnic_is_hashed_not_stored_raw(self):
    raw_cnic = '3520112345678'
    user = AuthService.register_user(self._valid_data(cnic=raw_cnic))
    self.assertNotEqual(user.cnic_hash, raw_cnic)

  def test_cnic_hash_matches_hash_cnic(self):
    raw_cnic = '3520112345678'
    user = AuthService.register_user(self._valid_data(cnic=raw_cnic))
    self.assertEqual(user.cnic_hash, AuthService.hash_cnic(raw_cnic))

  def test_full_name_not_stored_on_user_model(self):
    user = AuthService.register_user(self._valid_data(full_name = 'use2'))
    self.assertFalse(hasattr(user, 'full_name'))

  def test_cnic_not_stored_on_user_model(self):
    user = AuthService.register_user(self._valid_data(cnic = '3520112345678'))
    self.assertFalse(hasattr(user, 'cnic'))

  def test_atomic_rollback_if_profile_creation_fails(self):
    with patch('accounts.services.Profile.objects.create') as mock_create:
      mock_create.side_effect = Exception('DB error')
      with self.assertRaises(Exception):
        AuthService.register_user(self._valid_data())
    self.assertFalse(User.objects.filter(email = 'use2@pakremit.com').exists())

  def test_duplicate_email_raises_error(self):
    AuthService.register_user(self._valid_data())
    with self.assertRaises(Exception):
      AuthService.register_user(self._valid_data(username = 'user3', phone = '03005674536'))

class AuthServCheckAccLockoutTests(TestCase):

  def setUp(self):
    self.user = make_user()

  def test_returns_false_when_no_lockout(self):
    self.user.acc_locked_until = None
    self.assertFalse(AuthService.check_account_lockout(self.user))

  def test_returns_true_when_locked_and_time_not_passed(self):
    self.user.acc_locked_until = timezone.now() + timedelta(minutes=25)
    self.assertTrue(AuthService.check_account_lockout(self.user))

  def test_returns_false_when_lock_has_expired(self):
    self.user.acc_locked_until = timezone.now() - timedelta(minutes=1)
    self.assertFalse(AuthService.check_account_lockout(self.user))

  def test_returns_false_when_lock_expires_exactly_now(self):
    self.user.acc_locked_until = timezone.now() - timedelta(seconds=1)
    self.assertFalse(AuthService.check_account_lockout(self.user))

  def test_does_not_modify_user(self):
    original_lock = timezone.now() + timedelta(minutes=10)
    self.user.acc_locked_until = original_lock
    AuthService.check_account_lockout(self.user)
    self.assertEqual(self.user.acc_locked_until, original_lock)

class AuthServIncrFailedLoginTests(TestCase):

  def setUp(self):
    self.user = make_user()

  def test_increments_failed_attempts(self):
    self.user.failed_login_attempts = 0
    self.user.save()
    AuthService.increment_failed_login(self.user)
    self.user.refresh_from_db()
    self.assertEqual(self.user.failed_login_attempts, 1)

  def test_increments_from_existing_count(self):
    self.user.failed_login_attempts = 3
    self.user.save()
    AuthService.increment_failed_login(self.user)
    self.user.refresh_from_db()
    self.assertEqual(self.user.failed_login_attempts, 4)

  def test_locks_account_after_5_attempts(self):
    self.user.failed_login_attempts = 4
    self.user.save()
    AuthService.increment_failed_login(self.user)
    self.user.refresh_from_db()
    self.assertIsNotNone(self.user.acc_locked_until)

  def test_lock_duration_is_30_minutes(self):
    self.user.failed_login_attempts = 4
    self.user.save()
    before = timezone.now()
    AuthService.increment_failed_login(self.user)
    after = timezone.now()
    self.user.refresh_from_db()
    expected_min = before + timedelta(minutes=29, seconds=59)
    expected_max = after + timedelta(minutes=30, seconds=1)
    self.assertGreater(self.user.acc_locked_until, expected_min)
    self.assertLess(self.user.acc_locked_until, expected_max)

  def test_resets_counter_to_zero_after_lock(self):
    self.user.failed_login_attempts = 4
    self.user.save()
    AuthService.increment_failed_login(self.user)
    self.user.refresh_from_db()
    self.assertEqual(self.user.failed_login_attempts, 0)

  def test_does_not_lock_before_5_attempts(self):
    self.user.failed_login_attempts = 3
    self.user.save()
    AuthService.increment_failed_login(self.user)
    self.user.refresh_from_db()
    self.assertIsNone(self.user.acc_locked_until)

  def test_persists_to_database(self):
    self.user.failed_login_attempts = 0
    self.user.save()
    AuthService.increment_failed_login(self.user)
    fresh = User.objects.get(pk=self.user.pk)
    self.assertEqual(fresh.failed_login_attempts, 1)

class AuthSerResvFailLoginTests(TestCase):

  def setUp(self):
    self.user = make_user()

  def test_resets_counter_when_above_zero(self):
    self.user.failed_login_attempts = 3
    self.user.save()
    AuthService.reset_failed_login(self.user)
    self.user.refresh_from_db()
    self.assertEqual(self.user.failed_login_attempts, 0)

  def test_does_not_save_when_already_zero(self):
    self.user.failed_login_attempts = 0
    self.user.save()
    with patch.object(self.user, 'save') as mock_save:
      AuthService.reset_failed_login(self.user)
      mock_save.assert_not_called()

  def test_persists_reset_to_database(self):
    self.user.failed_login_attempts = 2
    self.user.save()
    AuthService.reset_failed_login(self.user)
    fresh = User.objects.get(pk=self.user.pk)
    self.assertEqual(fresh.failed_login_attempts, 0)

class AuthServRegOrUpdDevTests(TestCase):

  def setUp(self):
    self.user = make_user()

  def test_creates_new_device(self):
    AuthService.register_or_update_device(user=self.user, fingerprint = 'fp_rp23', device_type = 'web', ip = '192.168.1.1')
    self.assertTrue(UserDevice.objects.filter(user=self.user, device_fingerprint = 'fp_rp23').exists())

  def test_returns_device_instance(self):
    device = AuthService.register_or_update_device(user=self.user, fingerprint = 'fp_rp23', device_type = 'web', ip = '192.168.1.1')
    self.assertIsInstance(device, UserDevice)

  def test_updates_existing_device(self):
    AuthService.register_or_update_device(user=self.user, fingerprint = 'fp_rp23', device_type = 'web', ip = '192.168.1.1')
    AuthService.register_or_update_device(user=self.user, fingerprint = 'fp_rp23', device_type = 'android', ip = '10.0.0.1')
    self.assertEqual(UserDevice.objects.filter(user=self.user, device_fingerprint = 'fp_rp23').count(), 1)

  def test_updates_device_type_on_existing_device(self):
    AuthService.register_or_update_device(
      user=self.user, fingerprint = 'fp_rp23', device_type = 'web', ip = '192.168.1.1')
    device = AuthService.register_or_update_device(user=self.user, fingerprint = 'fp_rp23', device_type = 'ios', ip = '192.168.1.1')
    self.assertEqual(device.type, 'ios')

  def test_updates_ip_on_existing_device(self):
    AuthService.register_or_update_device(user=self.user, fingerprint = 'fp_rp23', device_type = 'web', ip = '192.168.1.1')
    device = AuthService.register_or_update_device(user=self.user, fingerprint = 'fp_rp23', device_type = 'web', ip = '10.0.0.99')
    self.assertEqual(device.last_ip, '10.0.0.99')

  def test_different_fingerprints_create_separate_devices(self):
    AuthService.register_or_update_device(user=self.user, fingerprint = 'fp_023', device_type = 'web', ip = '192.168.1.1')
    AuthService.register_or_update_device(user=self.user, fingerprint = 'fp_024', device_type = 'android', ip = '192.168.1.2')
    self.assertEqual(UserDevice.objects.filter(user=self.user).count(), 2)

  def test_stores_correct_device_type(self):
    device = AuthService.register_or_update_device(user=self.user, fingerprint = 'fp_ios', device_type = 'ios', ip = '192.168.1.1')
    self.assertEqual(device.type, 'ios')

  def test_stores_correct_ip(self):
    device = AuthService.register_or_update_device(user=self.user, fingerprint = 'fp_rps', device_type = 'web', ip = '10.10.10.10')
    self.assertEqual(device.last_ip, '10.10.10.10')

class AuthServUpdPassTests(TestCase):

  def setUp(self):
    self.user = make_user()

  def test_password_is_changed(self):
    old_password = self.user.password
    AuthService.update_password(self.user, 'user2212312')
    self.user.refresh_from_db()
    self.assertNotEqual(self.user.password, old_password)

  def test_new_password_is_valid(self):
    AuthService.update_password(self.user, 'user2212312')
    self.user.refresh_from_db()
    self.assertTrue(self.user.check_password('user2212312'))

  def test_old_password_no_longer_valid(self):
    AuthService.update_password(self.user, 'user22123123')
    self.user.refresh_from_db()
    self.assertFalse(self.user.check_password('user112312'))

  def test_last_pass_change_is_updated(self):
    before = timezone.now()
    AuthService.update_password(self.user, 'user22123123')
    self.user.refresh_from_db()
    self.assertGreaterEqual(self.user.last_pass_change, before)

  def test_persists_to_database(self):
    AuthService.update_password(self.user, 'user22123123')
    fresh = User.objects.get(pk=self.user.pk)
    self.assertTrue(fresh.check_password('user22123123'))
    

TEST_CACHE_SETTINGS = {
  'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
  },
  'circuit_breaker': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
  },
}

SIGNAL_PATH = 'accounts.signals.breaker_call'

def make_user(**kwargs):
  defaults = {'username': 'user3', 'email': 'user3@pakremit.com', 'phone': '03140148272', 'password': 'user312312', 'control': 'user'}
  defaults.update(kwargs)
  return User.objects.create_user(**defaults)

def mock_response(status_code):
  r = MagicMock()
  r.status_code = status_code
  return r

@override_settings(CACHES=TEST_CACHE_SETTINGS)
class TriggWalletCreaTests(TestCase):

  def test_signal_fires_on_user_creation(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      self.assertTrue(mock_bc.called)

  def test_signal_does_not_fire_on_user_update(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      user = make_user()
      mock_bc.reset_mock()
      user.control = 'merchant'
      user.save()
      self.assertFalse(mock_bc.called)

  def test_signal_fires_exactly_once_per_user_creation(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      self.assertEqual(mock_bc.call_count, 1)

@override_settings(CACHES=TEST_CACHE_SETTINGS)
class TriggWalletCreaPayloadTests(TestCase):

  def _get_payload(self, mock_bc):
    return json.loads(mock_bc.call_args[1].get('data'))

  def test_sends_correct_user_id(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      user = make_user()
      payload = self._get_payload(mock_bc)
      self.assertEqual(str(payload['user_id']), str(user.id))

  def test_sends_pkr_as_default_currency(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      payload = self._get_payload(mock_bc)
      self.assertEqual(payload['currency'], 'PKR')

  def test_sends_zero_initial_balance(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      payload = self._get_payload(mock_bc)
      self.assertEqual(payload['initial_balance'], '0.00')

  def test_payload_is_sent_as_string_not_dict(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      call_kwargs = mock_bc.call_args[1]
      self.assertIn('data', call_kwargs)
      self.assertNotIn('json', call_kwargs)
      self.assertIsInstance(call_kwargs['data'], str)

@override_settings(CACHES=TEST_CACHE_SETTINGS)
class TriggWalletCreaHeaderTests(TestCase):

  def test_sends_internal_token_header(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      headers = mock_bc.call_args[1].get('headers', {})
      self.assertIn('X-Internal-Token', headers)

  def test_internal_token_matches_settings_secret(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      headers = mock_bc.call_args[1].get('headers', {})
      self.assertEqual(headers['X-Internal-Token'], settings.INTERNAL_SERVICE_SECRET)

  def test_sends_hmac_signature_header(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      headers = mock_bc.call_args[1].get('headers', {})
      self.assertIn('X-Internal-Signature', headers)

  def test_sends_content_type_json_header(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      headers = mock_bc.call_args[1].get('headers', {})
      self.assertEqual(headers.get('Content-Type'), 'application/json')

@override_settings(CACHES=TEST_CACHE_SETTINGS)
class TriggWalletCreaURLTests(TestCase):

  def test_calls_correct_wallet_creation_url(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      url = mock_bc.call_args[0][2]
      self.assertIn('create-internal', url)
      self.assertNotIn('create_internal', url)

  def test_calls_wallet_service_port(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      url = mock_bc.call_args[0][2]
      self.assertIn('8001', url)

  def test_uses_wallet_breaker(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      breaker_name = mock_bc.call_args[0][0]
      self.assertEqual(breaker_name, 'wallet_breaker')

@override_settings(CACHES=TEST_CACHE_SETTINGS)
class TriggWalletCreaErrorHandlTests(TestCase):

  def test_logs_error_when_circuit_breaker_returns_error(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (None, 'circuit is open')
      with self.assertLogs('accounts.signals', level='ERROR') as cm:
        make_user()
      self.assertTrue(any('wallet' in line.lower() or 'failed' in line.lower() for line in cm.output))

  def test_logs_error_contains_user_id(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (None, 'circuit is open')
      with self.assertLogs('accounts.signals', level='ERROR') as cm:
        user = make_user()
      self.assertIn(str(user.id), '\n'.join(cm.output))

  def test_does_not_crash_when_wallet_service_down(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (None, 'connection refused')
      try:
        make_user()
      except Exception as exc:
        self.fail(f'Signal crashed when wallet service is down: {exc}')

  def test_logs_error_on_non_201_response(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(400), None)
      with self.assertLogs('accounts.signals', level='ERROR') as cm:
        make_user()
      self.assertTrue(any('400' in line or 'failed' in line.lower() for line in cm.output))

  def test_sets_timeout_on_breaker_call(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      make_user()
      self.assertEqual(mock_bc.call_args[1].get('timeout'), 5)

@override_settings(CACHES=TEST_CACHE_SETTINGS)
class TriggWalletCreaSignTests(TestCase):

  def test_signature_is_valid_hmac_sha256(self):
    with patch(SIGNAL_PATH) as mock_bc:
      mock_bc.return_value = (mock_response(201), None)
      user = make_user()
      headers = mock_bc.call_args[1].get('headers', {})
      sent_signature = headers.get('X-Internal-Signature')
      payload = {'user_id': str(user.id), 'currency': 'PKR', 'initial_balance': '0.00'}
      payload_str = json.dumps(payload, sort_keys=True)
      secret = settings.INTERNAL_SERVICE_SECRET
      expected_signature = hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()
      self.assertEqual(sent_signature, expected_signature)
      
      
REGISTER_URL = '/accounts/auth/register/'
LOGIN_URL = '/accounts/tokenobtainpair/'
PROFILE_URL = '/accounts/user/profile/'
UPDATE_PASSWORD_URL = '/accounts/user/update_password/'


def valid_register_payload(**overrides):
  data = {
    'email': 'usernew@pakremit.com',
    'phone': '03453308750',
    'username': 'usernew',
    'password': 'usernew12312',
    'password_confirm': 'usernew12312',
    'full_name': 'User New',
    'cnic': '3520112345678',
  }
  data.update(overrides)
  return data

class AuthViewSetRegTests(IdentityServiceTestCase):
  def test_register_returns_201_on_valid_data(self):
    with patch('accounts.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (__import__('unittest.mock', fromlist=['MagicMock']).MagicMock(status_code=201), None)
      response = self.client.post(REGISTER_URL, valid_register_payload(), format='json')
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)

  def test_register_returns_user_id_in_response(self):
    with patch('accounts.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (__import__('unittest.mock', fromlist=['MagicMock']).MagicMock(status_code=201), None)
      response = self.client.post(REGISTER_URL, valid_register_payload(), format='json')
    self.assertIn('user_id', response.data.get('data', {}))

  def test_register_creates_user_in_db(self):
    with patch('accounts.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (__import__('unittest.mock', fromlist=['MagicMock']).MagicMock(status_code=201), None)
      self.client.post(REGISTER_URL, valid_register_payload(), format='json')
    self.assertTrue(User.objects.filter(email='usernew@pakremit.com').exists())

  def test_register_creates_profile_in_db(self):
    with patch('accounts.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (__import__('unittest.mock', fromlist=['MagicMock']).MagicMock(status_code=201), None)
      self.client.post(REGISTER_URL, valid_register_payload(), format='json')
    user = User.objects.get(email='usernew@pakremit.com')
    self.assertTrue(Profile.objects.filter(user=user).exists())

  def test_register_requires_no_authentication(self):
    self.clear_authentication()
    with patch('accounts.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (__import__('unittest.mock', fromlist=['MagicMock']).MagicMock(status_code=201), None)
      response = self.client.post(REGISTER_URL, valid_register_payload(), format='json')
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)

  def test_register_returns_400_on_password_mismatch(self):
    payload = valid_register_payload(password_confirm='usernew123123')
    response = self.client.post(REGISTER_URL, payload, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_register_returns_400_on_duplicate_email(self):
    with patch('accounts.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (__import__('unittest.mock', fromlist=['MagicMock']).MagicMock(status_code=201), None)
      self.client.post(REGISTER_URL, valid_register_payload(), format='json')
      response = self.client.post(REGISTER_URL, valid_register_payload(username = 'user7', phone = '03096793458'), format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_register_returns_400_on_missing_email(self):
    payload = valid_register_payload()
    payload.pop('email')
    response = self.client.post(REGISTER_URL, payload, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_register_returns_400_on_missing_password(self):
    payload = valid_register_payload()
    payload.pop('password')
    response = self.client.post(REGISTER_URL, payload, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_register_returns_400_on_weak_password(self):
    payload = valid_register_payload(password='user', password_confirm='user')
    response = self.client.post(REGISTER_URL, payload, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairViewTests(IdentityServiceTestCase):
  def test_login_returns_200_on_valid_credentials(self):
    response = self.client.post(LOGIN_URL, {'email': 'user2@pakremit.com', 'password': 'user2'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_200_OK)

  def test_login_returns_access_token(self):
    response = self.client.post(LOGIN_URL, {'email': 'user2@pakremit.com', 'password': 'user2'}, format='json')
    self.assertIn('access', response.data)

  def test_login_returns_refresh_token(self):
    response = self.client.post(LOGIN_URL, {'email': 'user2@pakremit.com', 'password': 'user2'}, format='json')
    self.assertIn('refresh', response.data)

  def test_login_returns_custom_claims(self):
    response = self.client.post(LOGIN_URL, {'email': 'user2@pakremit.com', 'password': 'user2'}, format='json')
    self.assertIn('user_id', response.data)
    self.assertIn('control', response.data)
    self.assertIn('is_staff', response.data)
    self.assertIn('is_kyc_verified', response.data)

  def test_login_returns_400_on_wrong_password(self):
    response = self.client.post(LOGIN_URL, {'email': 'user2@pakremit.com', 'password': 'wrongpassword'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_login_returns_400_on_wrong_email(self):
    response = self.client.post(LOGIN_URL, {'email': 'nobody@pakremit.com', 'password': 'user212312'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_login_locks_account_after_5_failed_attempts(self):
    for _ in range(5):
      self.client.post(LOGIN_URL, {'email': 'user2@pakremit.com', 'password': 'user12312'}, format='json')
    response = self.client.post(LOGIN_URL, {'email': 'user2@pakremit.com', 'password': 'user2'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn('locked', str(response.data).lower())

  def test_login_returns_400_on_locked_account(self):
    self.verified_user.acc_locked_until = timezone.now() + timedelta(minutes=30)
    self.verified_user.save()
    response = self.client.post(LOGIN_URL, {'email': 'user2@pakremit.com', 'password': 'user2'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_login_registers_device(self):
    self.client.post(LOGIN_URL, {'email': 'user2@pakremit.com', 'password': 'user2', 'device_fingerprint': 'check-ud-view-23', 'device_type': 'web'}, format='json')
    self.assertTrue(UserDevice.objects.filter(user=self.verified_user, device_fingerprint = 'check-ud-view-23').exists())

class UserViewSetProfTests(IdentityServiceTestCase):
  def test_profile_returns_200_for_authenticated_user(self):
    self.authenticate_as('verified')
    response = self.client.get(PROFILE_URL)
    self.assertEqual(response.status_code, status.HTTP_200_OK)

  def test_profile_returns_401_for_unauthenticated_user(self):
    self.clear_authentication()
    response = self.client.get(PROFILE_URL)
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

  def test_profile_returns_correct_email(self):
    self.authenticate_as('verified')
    response = self.client.get(PROFILE_URL)
    self.assertEqual(response.data['email'], self.verified_user.email)

  def test_profile_returns_correct_username(self):
    self.authenticate_as('verified')
    response = self.client.get(PROFILE_URL)
    self.assertEqual(response.data['username'], self.verified_user.username)

  def test_profile_returns_correct_control(self):
    self.authenticate_as('verified')
    response = self.client.get(PROFILE_URL)
    self.assertEqual(response.data['control'], 'user')

  def test_admin_can_access_own_profile(self):
    self.authenticate_as('admin')
    response = self.client.get(PROFILE_URL)
    self.assertEqual(response.status_code, status.HTTP_200_OK)

  def test_merchant_can_access_own_profile(self):
    self.authenticate_as('merchant')
    response = self.client.get(PROFILE_URL)
    self.assertEqual(response.status_code, status.HTTP_200_OK)

class UserViewSetUpdPassTests(IdentityServiceTestCase):
  def test_returns_200_on_correct_old_password(self):
    self.authenticate_as('verified')
    response = self.client.patch(UPDATE_PASSWORD_URL, {'old_password': 'user2', 'new_password': 'user212312'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_200_OK)

  def test_returns_400_on_wrong_old_password(self):
    self.authenticate_as('verified')
    response = self.client.patch(UPDATE_PASSWORD_URL, {'old_password': 'user223', 'new_password': 'user2123122'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_returns_400_on_missing_old_password(self):
    self.authenticate_as('verified')
    response = self.client.patch(UPDATE_PASSWORD_URL, {'new_password': 'user212312'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_returns_400_on_missing_new_password(self):
    self.authenticate_as('verified')
    response = self.client.patch(UPDATE_PASSWORD_URL, {'old_password': 'user2'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_returns_400_on_weak_new_password(self):
    self.authenticate_as('verified')
    response = self.client.patch(UPDATE_PASSWORD_URL, {'old_password': 'user2', 'new_password': 'user2123'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_returns_401_for_unauthenticated_user(self):
    self.clear_authentication()
    response = self.client.patch(UPDATE_PASSWORD_URL, {'old_password': 'user2', 'new_password': 'user212312'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

  def test_new_password_actually_works_after_update(self):
    self.authenticate_as('verified')
    self.client.patch(UPDATE_PASSWORD_URL, {'old_password': 'user2', 'new_password': 'user212312'}, format='json')
    self.verified_user.refresh_from_db()
    self.assertTrue(self.verified_user.check_password('user212312'))

  def test_old_password_no_longer_works_after_update(self):
    self.authenticate_as('verified')
    self.client.patch(UPDATE_PASSWORD_URL, {'old_password': 'user2', 'new_password': 'user212312'}, format='json')
    self.verified_user.refresh_from_db()
    self.assertFalse(self.verified_user.check_password('user2'))