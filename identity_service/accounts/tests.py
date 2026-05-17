from accounts.models import User, Profile, UserDevice
from django.test import TestCase
from accounts.services import AuthService
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch

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