from parent.tests.parent import ParentTestCase
from kyc.models import KYCProfile, VerificationLog
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from parent.permissions import PakRemitPermission
from kyc.permissions import AdminPermission, KYCVerifiedPermission
from django.contrib.auth.models import AnonymousUser
from accounts.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from kyc.services import KYCService, BiometricService
from django.db import IntegrityError
from unittest.mock import patch, MagicMock
import time
from kyc.tasks import expire_old_kycs, check_kyc_expiry
import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

class IdentityServiceTestCase(ParentTestCase):
    @classmethod
    def setUpTestData(cls):
      super().setUpTestData()
      cls.verified_kyc = KYCProfile.objects.create(user=cls.verified_user, status = 'approved', tier = 'tier2', is_verified=True,
        verified_at=timezone.now(), expires_at=timezone.now() + timedelta(days=40))
      cls.merchant_kyc = KYCProfile.objects.create(user=cls.merchant, status = 'approved', tier = 'tier3', is_verified=True,
        verified_at=timezone.now(), expires_at=timezone.now() + timedelta(days=50))
      cls.agent_kyc = KYCProfile.objects.create(user=cls.agent, status = 'approved', tier = 'tier2', is_verified=True, verified_at=timezone.now(),
        expires_at=timezone.now() + timedelta(days=60))
      cls.expired_kyc = KYCProfile.objects.create(user=cls.expired_kyc_user, status = 'expired', tier = 'tier1', is_verified=False, verified_at=timezone.now() - timedelta(days=20),
        expires_at=timezone.now() - timedelta(days=70))
      cls.pending_kyc = KYCProfile.objects.create(user=cls.pending_kyc_user, status = 'pending', tier = 'tier1', is_verified=False)
       
factory = APIRequestFactory()
view = APIView()

def make_request(method = 'get', path='/'):
  if method == 'post':
    return factory.post(path)
  return factory.get(path)

# class PakRemitHasPermissionTests(IdentityServiceTestCase):

#   def setUp(self):
#     super().setUp()
#     self.perm = PakRemitPermission()

#   def test_denies_when_request_auth_is_none(self):
#     request = make_request()
#     request.auth = None
#     self.assertFalse(self.perm.has_permission(request, view))

#   def test_denies_unverified_regular_user(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.regular_user, is_kyc_verified=False)
#     self.assertFalse(self.perm.has_permission(request, view))

#   def test_denies_expired_kyc_user(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.expired_kyc_user, is_kyc_verified=False)
#     self.assertFalse(self.perm.has_permission(request, view))

#   def test_denies_pending_kyc_user(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.pending_kyc_user, is_kyc_verified=False)
#     self.assertFalse(self.perm.has_permission(request, view))

#   def test_allows_kyc_verified_user(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.verified_user, is_kyc_verified=True)
#     self.assertTrue(self.perm.has_permission(request, view))

#   def test_allows_kyc_verified_merchant(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.merchant, is_kyc_verified=True)
#     self.assertTrue(self.perm.has_permission(request, view))

#   def test_allows_kyc_verified_agent(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.agent, is_kyc_verified=True)
#     self.assertTrue(self.perm.has_permission(request, view))

#   def test_allows_admin_without_kyc(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.admin, is_kyc_verified=False)
#     self.assertTrue(self.perm.has_permission(request, view))

#   def test_allows_staff_without_kyc(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.staff_user, is_kyc_verified=False)
#     self.assertTrue(self.perm.has_permission(request, view))

#   def test_denies_unknown_control_even_if_kyc_verified(self):
#     request = make_request()
#     request.auth = {'user_id': str(self.verified_user.pk), 'control': 'unknown_role', 'is_staff': False, 'is_kyc_verified': True}
#     self.assertFalse(self.perm.has_permission(request, view))

# class PakRemitHasObjectPermTests(IdentityServiceTestCase):

#   def setUp(self):
#     super().setUp()
#     self.perm = PakRemitPermission()

#   def _make_obj(self, **kwargs):
#     class Obj:
#       pass
#     o = Obj()
#     for k, v in kwargs.items():
#       setattr(o, k, v)
#     return o

#   def test_denies_when_auth_is_none(self):
#     request = make_request()
#     request.auth = None
#     obj = self._make_obj(user_id=str(self.verified_user.pk))
#     self.assertFalse(self.perm.has_object_permission(request, view, obj))

#   def test_admin_can_access_any_object(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.admin, control = 'admin')
#     obj = self._make_obj(user_id=str(self.verified_user.pk))
#     self.assertTrue(self.perm.has_object_permission(request, view, obj))

#   def test_user_can_access_own_user_object(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.verified_user)
#     self.assertTrue(self.perm.has_object_permission(request, view, self.verified_user))

#   def test_user_cannot_access_another_users_object(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.verified_user)
#     self.assertFalse(self.perm.has_object_permission(request, view, self.merchant))

#   def test_ownership_via_user_fk_object(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.verified_user)
#     inner = type('U', (), {'id': self.verified_user.pk})()
#     obj = self._make_obj(user=inner)
#     self.assertTrue(self.perm.has_object_permission(request, view, obj))

#   def test_ownership_via_user_fk_raw_id(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.verified_user)
#     obj = self._make_obj(user=self.verified_user.pk)
#     self.assertTrue(self.perm.has_object_permission(request, view, obj))

#   def test_ownership_via_user_id_field(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.verified_user)
#     obj = self._make_obj(user_id=self.verified_user.pk)
#     self.assertTrue(self.perm.has_object_permission(request, view, obj))

#   def test_ownership_via_owner_id_field(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.verified_user)
#     obj = self._make_obj(owner_id=self.verified_user.pk)
#     self.assertTrue(self.perm.has_object_permission(request, view, obj))

#   def test_ownership_via_customer_id_field(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.verified_user)
#     obj = self._make_obj(customer_id=self.verified_user.pk)
#     self.assertTrue(self.perm.has_object_permission(request, view, obj))

#   def test_denies_when_no_ownership_field_present(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.verified_user)
#     obj = self._make_obj(amount=500, currency = 'pkr')
#     self.assertFalse(self.perm.has_object_permission(request, view, obj))

#   def test_wrong_owner_via_user_id_field_denied(self):
#     request = make_request()
#     request.auth = self.make_auth_dict(self.verified_user)
#     obj = self._make_obj(user_id=self.merchant.pk)
#     self.assertFalse(self.perm.has_object_permission(request, view, obj))

# class AdminPermission_Tests(IdentityServiceTestCase):

#   def setUp(self):
#     super().setUp()
#     self.perm = AdminPermission()

#   def _req(self, user, control=None, is_staff=None):
#     request = make_request(method = 'post')
#     request.user = user
#     request.auth = self.make_auth_dict(user, control=control, is_staff=is_staff)
#     return request

#   def test_denies_when_user_is_none(self):
#     request = make_request()
#     request.user = None
#     request.auth = {}
#     self.assertFalse(self.perm.has_permission(request, view))

#   def test_denies_unauthenticated_user(self):
#     request = make_request()
#     request.user = AnonymousUser()
#     request.auth = {}
#     self.assertFalse(self.perm.has_permission(request, view))

#   def test_allows_admin_control(self):
#     request = self._req(self.admin, control = 'admin')
#     self.assertTrue(self.perm.has_permission(request, view))

#   def test_allows_is_staff_true(self):
#     request = self._req(self.staff_user, is_staff=True)
#     self.assertTrue(self.perm.has_permission(request, view))

#   def test_denies_verified_regular_user(self):
#     request = self._req(self.verified_user)
#     self.assertFalse(self.perm.has_permission(request, view))

#   def test_denies_merchant(self):
#     request = self._req(self.merchant)
#     self.assertFalse(self.perm.has_permission(request, view))

#   def test_denies_agent(self):
#     request = self._req(self.agent)
#     self.assertFalse(self.perm.has_permission(request, view))

# class KYCVerifiedPermTests(IdentityServiceTestCase):
#   def setUp(self):
#     super().setUp()
#     self.perm = KYCVerifiedPermission()

#   def test_denies_when_user_is_none(self):
#     request = make_request()
#     request.user = None
#     self.assertFalse(self.perm.has_permission(request, view))

#   def test_denies_unauthenticated_user(self):
#     request = make_request()
#     request.user = AnonymousUser()
#     request.auth = {}
#     self.assertFalse(self.perm.has_permission(request, view))

#   def test_allows_verified_user(self):
#     request = make_request()
#     request.user = self.verified_user
#     request.auth = self.make_auth_dict(self.verified_user, is_kyc_verified=True)
#     self.assertTrue(self.perm.has_permission(request, view))

#   def test_denies_unverified_user(self):
#     request = make_request()
#     request.user = self.regular_user
#     request.auth = {'user_id': str(self.regular_user.pk), 'is_kyc_verified': False}
#     self.assertFalse(self.perm.has_permission(request, view))
    
    
# def make_user(email = 'user1@pakremit.com', **kwargs):
#     return User.objects.create_user(email=email, username=kwargs.get('username', 'user1'), password = 'user112312', phone=kwargs.get('phone', '03294567451'))

# def make_admin():
#     return User.objects.create_user(email = 'admin@pakremit.com', username = 'admin', password = 'admin12312', phone = '03034567823', is_staff=True, control = 'admin')

# def fake_image(name='test.jpg'):
#     return SimpleUploadedFile(name, b'fakeimagecontent', content_type = 'image/jpeg')

# class KYCProfileModelTests(TestCase):
#   def setUp(self):
#     self.user = make_user()
#     self.admin = make_admin()

#   def test_kyc_default_status_is_pending(self):
#     kyc = KYCProfile.objects.create(user=self.user)
#     self.assertEqual(kyc.status, 'pending')

#   def test_kyc_default_tier_is_tier1(self):
#     kyc = KYCProfile.objects.create(user=self.user)
#     self.assertEqual(kyc.tier, 'tier1')

#   def test_kyc_is_not_verified_by_default(self):
#     kyc = KYCProfile.objects.create(user=self.user)
#     self.assertFalse(kyc.is_verified)

#   def test_kyc_can_transition_from_pending_to_approved(self):
#     kyc = KYCProfile.objects.create(user=self.user)
#     kyc.status = 'approved'
#     kyc.is_verified = True
#     kyc.save()
#     kyc.refresh_from_db()
#     self.assertEqual(kyc.status, 'approved')
#     self.assertTrue(kyc.is_verified)

#   def test_kyc_approved_resets_to_pending_on_resubmit(self):
#     kyc = KYCProfile.objects.create(user=self.user, status='approved', is_verified=True)
#     updated = KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     updated.refresh_from_db()
#     self.assertEqual(updated.status, 'pending')
#     self.assertFalse(updated.is_verified)

#   def test_kyc_expiry_is_set_on_approval(self):
#     kyc = KYCProfile.objects.create(user=self.user)
#     before = timezone.now()
#     KYCService.approve_kyc(kyc, self.admin)
#     kyc.refresh_from_db()
#     expected_expiry = before + timedelta(days=30)
#     self.assertAlmostEqual(kyc.expires_at.timestamp(), expected_expiry.timestamp(), delta=5)

#   def test_same_user_cannot_have_two_kyc_profiles(self):
#     KYCProfile.objects.create(user=self.user)
#     with self.assertRaises(IntegrityError):
#       KYCProfile.objects.create(user=self.user)

#   def test_rejected_kyc_sets_is_verified_false(self):
#     kyc = KYCProfile.objects.create(user=self.user, status = 'approved', is_verified=True)
#     KYCService.reject_kyc(kyc, 'documents unclear', self.admin)
#     kyc.refresh_from_db()
#     self.assertFalse(kyc.is_verified)
#     self.assertEqual(kyc.status, 'rejected')

# class BiometricServiceTests(TestCase):
#   def test_hash_biometric_data_returns_string(self):
#     result = BiometricService.hash_biometric_data('raw_scan_data')
#     self.assertIsInstance(result, str)

#   def test_hash_biometric_data_returns_64_char_sha256(self):
#     result = BiometricService.hash_biometric_data('raw_scan_data')
#     self.assertEqual(len(result), 64)

#   def test_hash_biometric_data_is_deterministic(self):
#     result1 = BiometricService.hash_biometric_data('same_input')
#     result2 = BiometricService.hash_biometric_data('same_input')
#     self.assertEqual(result1, result2)

#   def test_hash_biometric_different_inputs_give_different_hashes(self):
#     result1 = BiometricService.hash_biometric_data('input_one')
#     result2 = BiometricService.hash_biometric_data('input_two')
#     self.assertNotEqual(result1, result2)

#   def test_verify_with_nadra_takes_at_least_1_second(self):
#     start = time.time()
#     BiometricService.verify_with_nadra('somehash')
#     elapsed = time.time() - start
#     self.assertGreaterEqual(elapsed, 1.0)

#   def test_verify_with_nadra_returns_bool(self):
#     result = BiometricService.verify_with_nadra('somehash')
#     self.assertIsInstance(result, bool)

#   def test_verify_with_nadra_empty_hash_returns_false(self):
#     result = BiometricService.verify_with_nadra('')
#     self.assertFalse(result)

#   def test_verify_with_nadra_none_returns_false(self):
#     result = BiometricService.verify_with_nadra(None)
#     self.assertFalse(result)

#   def test_verify_with_nadra_succeeds_90_percent(self):
#     with patch('time.sleep'):
#       results = [BiometricService.verify_with_nadra('valid_hash') for _ in range(100)]
#     success_rate = sum(results) / 100
#     self.assertGreater(success_rate, 0.75)
#     self.assertLess(success_rate, 1.0)

# class KYCServiceTests(TestCase):
#   def setUp(self):
#     self.user = make_user()
#     self.admin = make_admin()

#   def test_submit_kyc_creates_kyc_profile(self):
#     KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     self.assertTrue(KYCProfile.objects.filter(user=self.user).exists())

#   def test_submit_kyc_creates_verification_log(self):
#     KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     kyc = KYCProfile.objects.get(user=self.user)
#     self.assertTrue(VerificationLog.objects.filter(kyc_profile=kyc).exists())

#   def test_submit_kyc_sets_status_to_pending(self):
#     kyc = KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     self.assertEqual(kyc.status, 'pending')

#   def test_submit_kyc_twice_updates_existing_not_creates_new(self):
#     KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     count = KYCProfile.objects.filter(user=self.user).count()
#     self.assertEqual(count, 1)

#   def test_submit_kyc_resets_verified_status_on_resubmit(self):
#     kyc = KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     KYCService.approve_kyc(kyc, self.admin)
#     KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     kyc.refresh_from_db()
#     self.assertFalse(kyc.is_verified)
#     self.assertEqual(kyc.status, 'pending')

#   def test_approve_kyc_sets_is_verified_true(self):
#     kyc = KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     KYCService.approve_kyc(kyc, self.admin)
#     kyc.refresh_from_db()
#     self.assertTrue(kyc.is_verified)

#   def test_approve_kyc_sets_correct_tier(self):
#     kyc = KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     KYCService.approve_kyc(kyc, self.admin, tier = 'tier2')
#     kyc.refresh_from_db()
#     self.assertEqual(kyc.tier, 'tier2')

#   def test_approve_kyc_sets_verified_by(self):
#     kyc = KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     KYCService.approve_kyc(kyc, self.admin)
#     kyc.refresh_from_db()
#     self.assertEqual(kyc.verified_by, self.admin)

#   def test_approve_kyc_creates_verification_log(self):
#     kyc = KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     KYCService.approve_kyc(kyc, self.admin)
#     logs = VerificationLog.objects.filter(kyc_profile=kyc, status = 'approved')
#     self.assertTrue(logs.exists())

#   def test_reject_kyc_sets_status_rejected(self):
#     kyc = KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     KYCService.reject_kyc(kyc, 'blurry documents', self.admin)
#     kyc.refresh_from_db()
#     self.assertEqual(kyc.status, 'rejected')

#   def test_reject_kyc_stores_rejection_reason(self):
#     kyc = KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     KYCService.reject_kyc(kyc, 'blurry documents', self.admin)
#     kyc.refresh_from_db()
#     self.assertEqual(kyc.rej_reason, 'blurry documents')

#   def test_reject_kyc_creates_verification_log(self):
#     kyc = KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     KYCService.reject_kyc(kyc, 'blurry documents', self.admin)
#     logs = VerificationLog.objects.filter(kyc_profile=kyc, status = 'rejected')
#     self.assertTrue(logs.exists())

#   def test_approve_kyc_triggers_wallet_tier_upgrade_signal(self):
#     kyc = KYCService.submit_kyc(self.user, fake_image(), fake_image())
#     with patch('kyc.signals.breaker_call') as mock_bc:
#       mock_bc.return_value = (MagicMock(status_code=200), None)
#       KYCService.approve_kyc(kyc, self.admin, tier = 'tier2')
#       self.assertTrue(mock_bc.called)
    
      
# class KYCSignalTests(IdentityServiceTestCase):
#   def test_signal_fires_breaker_call_on_kyc_approval(self):
#     kyc = KYCProfile.objects.create(user=self.regular_user, status='pending', is_verified=False)
#     with patch('kyc.signals.breaker_call') as mock_bc:
#       mock_bc.return_value = (MagicMock(status_code=200), None)
#       kyc.status = 'approved'
#       kyc.is_verified = True
#       kyc.save()
#       self.assertTrue(mock_bc.called)

#   def test_signal_does_not_fire_on_pending_status(self):
#     kyc = KYCProfile.objects.create(user=self.regular_user, status='pending', is_verified=False)
#     with patch('kyc.signals.breaker_call') as mock_bc:
#       mock_bc.return_value = (MagicMock(status_code=200), None)
#       kyc.status = 'pending'
#       kyc.save()
#       mock_bc.assert_not_called()

#   def test_signal_does_not_fire_on_rejected_status(self):
#     kyc = KYCProfile.objects.create(user=self.regular_user, status='pending', is_verified=False)
#     with patch('kyc.signals.breaker_call') as mock_bc:
#       mock_bc.return_value = (MagicMock(status_code=200), None)
#       kyc.status = 'rejected'
#       kyc.save()
#       mock_bc.assert_not_called()

#   def test_signal_does_not_fire_when_approved_but_not_verified(self):
#     kyc = KYCProfile.objects.create(user=self.regular_user, status = 'pending', is_verified=False)
#     with patch('kyc.signals.breaker_call') as mock_bc:
#       mock_bc.return_value = (MagicMock(status_code=200), None)
#       kyc.status = 'approved'
#       kyc.is_verified = False
#       kyc.save()
#       mock_bc.assert_not_called()

#   def test_signal_logs_error_when_circuit_breaker_returns_error(self):
#     kyc = KYCProfile.objects.create(user=self.regular_user, status = 'pending', is_verified=False)
#     with patch('kyc.signals.breaker_call') as mock_bc:
#       with patch('kyc.signals.logger') as mock_logger:
#         mock_bc.return_value = (None, 'wallet service unavailable')
#         kyc.status = 'approved'
#         kyc.is_verified = True
#         kyc.save()
#         mock_logger.error.assert_called_once()

#   def test_signal_sends_correct_tier_in_payload(self):
#     kyc = KYCProfile.objects.create(user=self.regular_user, status = 'pending', is_verified=False, tier = 'tier2')
#     with patch('kyc.signals.breaker_call') as mock_bc:
#       mock_bc.return_value = (MagicMock(status_code=200), None)
#       kyc.status = 'approved'
#       kyc.is_verified = True
#       kyc.save()
#       call_kwargs = mock_bc.call_args
#       json_payload = call_kwargs.kwargs.get('json', {})
#       self.assertEqual(json_payload.get('tier'), 'tier2')

#   def test_signal_uses_wallet_breaker(self):
#     kyc = KYCProfile.objects.create(user=self.regular_user, status='pending', is_verified=False)
#     with patch('kyc.signals.breaker_call') as mock_bc:
#       mock_bc.return_value = (MagicMock(status_code=200), None)
#       kyc.status = 'approved'
#       kyc.is_verified = True
#       kyc.save()
#       breaker_name = mock_bc.call_args.args[0]
#       self.assertEqual(breaker_name, 'wallet_breaker')

#   def test_signal_does_not_raise_exception_when_wallet_service_down(self):
#     kyc = KYCProfile.objects.create(user=self.regular_user, status = 'pending', is_verified=False)
#     with patch('kyc.signals.breaker_call') as mock_bc:
#       mock_bc.return_value = (None, 'connection refused')
#       try:
#         kyc.status = 'approved'
#         kyc.is_verified = True
#         kyc.save()
#       except Exception:
#         self.fail('the sig raised an excep when the wallet service wasnt working')
   
        
KYC_SUBMIT_URL = '/kyc/kycview/submit/'
KYC_LIST_URL = '/kyc/kycview/'

def kyc_approve_url(pk):
  return f'/kyc/kycview/{pk}/approve/'

def kyc_reject_url(pk):
  return f'/kyc/kycview/{pk}/reject/'

def kyc_biometric_url():
  return '/kyc/kycview/verify_biometric/'

def fake_image(name = 'test.jpg'):
  img = Image.new('RGB', (100, 100), color = 'red')
  buf = io.BytesIO()
  img.save(buf, format='JPEG')
  buf.seek(0)
  return SimpleUploadedFile(name, buf.read(), content_type='image/jpeg')

class KYCViewSetSubmitTests(IdentityServiceTestCase):
  def test_submit_returns_201_with_valid_images(self):
    self.authenticate_as('regular')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      response = self.client.post(KYC_SUBMIT_URL, {'cnic_front_image': fake_image('front.jpg'), 'cnic_back_image': fake_image('back.jpg')}, format='multipart')
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)

  def test_submit_returns_400_without_cnic_front(self):
    self.authenticate_as('regular')
    response = self.client.post(KYC_SUBMIT_URL, {'cnic_back_image': fake_image('back.jpg')}, format='multipart')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_submit_returns_400_without_cnic_back(self):
    self.authenticate_as('regular')
    response = self.client.post(KYC_SUBMIT_URL, {'cnic_front_image': fake_image('front.jpg')}, format='multipart')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_submit_returns_401_for_unauthenticated_user(self):
    self.clear_authentication()
    response = self.client.post(KYC_SUBMIT_URL, {'cnic_front_image': fake_image(), 'cnic_back_image': fake_image()}, format='multipart')
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

  def test_submit_creates_kyc_profile_in_db(self):
    self.authenticate_as('regular')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      self.client.post(KYC_SUBMIT_URL, {'cnic_front_image': fake_image('front.jpg'), 'cnic_back_image': fake_image('back.jpg')}, format='multipart')
    self.assertTrue(KYCProfile.objects.filter(user=self.regular_user).exists())

  def test_submit_creates_verification_log(self):
    self.authenticate_as('regular')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      self.client.post(KYC_SUBMIT_URL, {'cnic_front_image': fake_image('front.jpg'), 'cnic_back_image': fake_image('back.jpg')}, format='multipart')
    kyc = KYCProfile.objects.get(user=self.regular_user)
    self.assertTrue(VerificationLog.objects.filter(kyc_profile=kyc).exists())

  def test_submit_blocked_when_kyc_already_pending(self):
    self.authenticate_as('regular')
    KYCProfile.objects.create(user=self.regular_user, status='pending')
    response = self.client.post(KYC_SUBMIT_URL, {'cnic_front_image': fake_image('front.jpg'), 'cnic_back_image': fake_image('back.jpg')}, format='multipart')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_submit_blocked_when_kyc_already_approved(self):
    self.authenticate_as('verified')
    response = self.client.post(KYC_SUBMIT_URL, {'cnic_front_image': fake_image('front.jpg'), 'cnic_back_image': fake_image('back.jpg')}, format='multipart')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_submit_allowed_when_kyc_is_rejected(self):
    KYCProfile.objects.create(user=self.regular_user, status='rejected')
    self.regular_user.refresh_from_db()
    self.authenticate_as('regular')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      response = self.client.post(KYC_SUBMIT_URL, {'cnic_front_image': fake_image('front.jpg'), 'cnic_back_image': fake_image('back.jpg')}, format='multipart')
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)

  def test_submit_response_contains_status_field(self):
    self.authenticate_as('regular')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      response = self.client.post(KYC_SUBMIT_URL, {'cnic_front_image': fake_image('front.jpg'), 'cnic_back_image': fake_image('back.jpg')}, format='multipart')
    self.assertIn('status', response.data)

  def test_submit_sets_initial_status_to_pending(self):
    self.authenticate_as('regular')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      response = self.client.post(KYC_SUBMIT_URL, {'cnic_front_image': fake_image('front.jpg'), 'cnic_back_image': fake_image('back.jpg')}, format='multipart')
    self.assertEqual(response.data['status'], 'pending')

class KYCViewSetApproveTests(IdentityServiceTestCase):
  def test_approve_returns_200_for_admin(self):
    self.authenticate_as('admin')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      response = self.client.post(kyc_approve_url(self.pending_kyc.id), {'tier': 'tier2'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_200_OK)

  def test_approve_returns_403_for_regular_user(self):
    self.authenticate_as('verified')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      response = self.client.post(kyc_approve_url(self.pending_kyc.id), {'tier': 'tier2'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

  def test_approve_returns_403_for_merchant(self):
    self.authenticate_as('merchant')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      response = self.client.post(kyc_approve_url(self.pending_kyc.id), {'tier': 'tier2'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

  def test_approve_sets_kyc_status_to_approved(self):
    self.authenticate_as('admin')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      self.client.post(kyc_approve_url(self.pending_kyc.id), {'tier': 'tier1'}, format='json')
    self.pending_kyc.refresh_from_db()
    self.assertEqual(self.pending_kyc.status, 'approved')

  def test_approve_sets_correct_tier(self):
    self.authenticate_as('admin')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      self.client.post(kyc_approve_url(self.pending_kyc.id), {'tier': 'tier3'}, format='json')
    self.pending_kyc.refresh_from_db()
    self.assertEqual(self.pending_kyc.tier, 'tier3')

  def test_approve_sets_is_verified_true(self):
    self.authenticate_as('admin')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      self.client.post(kyc_approve_url(self.pending_kyc.id), {'tier': 'tier1'}, format='json')
    self.pending_kyc.refresh_from_db()
    self.assertTrue(self.pending_kyc.is_verified)

  def test_approve_with_invalid_tier_returns_400(self):
    self.authenticate_as('admin')
    with patch('kyc.signals.breaker_call') as mock_bc:
      mock_bc.return_value = (MagicMock(status_code=200), None)
      response = self.client.post(kyc_approve_url(self.pending_kyc.id), {'tier': 'invalid_tier'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_approve_returns_401_for_unauthenticated(self):
    self.clear_authentication()
    response = self.client.post(kyc_approve_url(self.pending_kyc.id), {'tier': 'tier1'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class KYCViewSetRejectTests(IdentityServiceTestCase):
  def test_reject_returns_200_for_admin(self):
    self.authenticate_as('admin')
    response = self.client.post(kyc_reject_url(self.pending_kyc.id), {'reason': 'blurry docs'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_200_OK)

  def test_reject_returns_403_for_regular_user(self):
    self.authenticate_as('verified')
    response = self.client.post(kyc_reject_url(self.pending_kyc.id), {'reason': 'blurry docs'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

  def test_reject_sets_status_to_rejected(self):
    self.authenticate_as('admin')
    self.client.post(kyc_reject_url(self.pending_kyc.id), {'reason': 'blurry docs'}, format='json')
    self.pending_kyc.refresh_from_db()
    self.assertEqual(self.pending_kyc.status, 'rejected')

  def test_reject_stores_reason_in_db(self):
    self.authenticate_as('admin')
    self.client.post(kyc_reject_url(self.pending_kyc.id), {'reason': 'blurry docs'}, format='json')
    self.pending_kyc.refresh_from_db()
    self.assertEqual(self.pending_kyc.rej_reason, 'blurry docs')

  def test_reject_sets_is_verified_false(self):
    self.authenticate_as('admin')
    self.pending_kyc.is_verified = True
    self.pending_kyc.save()
    self.client.post(kyc_reject_url(self.pending_kyc.id), {'reason': 'blurry docs'}, format='json')
    self.pending_kyc.refresh_from_db()
    self.assertFalse(self.pending_kyc.is_verified)

  def test_reject_without_reason_uses_default(self):
    self.authenticate_as('admin')
    self.client.post(kyc_reject_url(self.pending_kyc.id), {}, format='json')
    self.pending_kyc.refresh_from_db()
    self.assertEqual(self.pending_kyc.rej_reason, 'unclear documents')

  def test_reject_creates_verification_log(self):
    self.authenticate_as('admin')
    self.client.post(kyc_reject_url(self.pending_kyc.id), {'reason': 'blurry docs'}, format='json')
    logs = VerificationLog.objects.filter(kyc_profile=self.pending_kyc, status='rejected')
    self.assertTrue(logs.exists())

class KYCViewSetListTests(IdentityServiceTestCase):
  def test_list_returns_200_for_admin(self):
    self.authenticate_as('admin')
    response = self.client.get(KYC_LIST_URL)
    self.assertEqual(response.status_code, status.HTTP_200_OK)

  def test_list_returns_403_for_regular_user(self):
    self.authenticate_as('verified')
    response = self.client.get(KYC_LIST_URL)
    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

  def test_list_returns_all_kyc_profiles_for_admin(self):
    self.authenticate_as('admin')
    response = self.client.get(KYC_LIST_URL)
    self.assertGreaterEqual(len(response.data), 2)

  def test_list_returns_401_for_unauthenticated(self):
    self.clear_authentication()
    response = self.client.get(KYC_LIST_URL)
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class KYCViewSetBiometricTests(IdentityServiceTestCase):
  def test_biometric_returns_400_without_raw_input(self):
    self.authenticate_as('verified')
    response = self.client.post(kyc_biometric_url(), {}, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_biometric_returns_401_for_unauthenticated(self):
    self.clear_authentication()
    response = self.client.post(kyc_biometric_url(), {'biometric_raw': 'some_data'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

  def test_biometric_returns_200_on_successful_verification(self):
    self.authenticate_as('verified')
    with patch('kyc.services.BiometricService.verify_with_nadra') as mock_nadra:
      mock_nadra.return_value = True
      response = self.client.post(kyc_biometric_url(), {'biometric_raw': 'valid_scan_data'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_200_OK)

  def test_biometric_returns_400_on_failed_verification(self):
    self.authenticate_as('verified')
    with patch('kyc.services.BiometricService.verify_with_nadra') as mock_nadra:
      mock_nadra.return_value = False
      response = self.client.post(kyc_biometric_url(), {'biometric_raw': 'invalid_scan_data'}, format='json')
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

  def test_biometric_sets_is_biometric_verified_true_in_db(self):
    self.authenticate_as('verified')
    with patch('kyc.services.BiometricService.verify_with_nadra') as mock_nadra:
      mock_nadra.return_value = True
      self.client.post(kyc_biometric_url(), {'biometric_raw': 'valid_scan_data'}, format='json')
    self.verified_kyc.refresh_from_db()
    self.assertTrue(self.verified_kyc.is_biometric_verified)

  def test_biometric_stores_hash_in_db(self):
    self.authenticate_as('verified')
    with patch('kyc.services.BiometricService.verify_with_nadra') as mock_nadra:
      mock_nadra.return_value = True
      self.client.post(kyc_biometric_url(), {'biometric_raw': 'valid_scan_data'}, format='json')
    self.verified_kyc.refresh_from_db()
    self.assertIsNotNone(self.verified_kyc.biometric_hash)

  def test_biometric_creates_kyc_profile_if_not_exists(self):
    self.authenticate_as('regular')
    with patch('kyc.services.BiometricService.verify_with_nadra') as mock_nadra:
      mock_nadra.return_value = True
      self.client.post(kyc_biometric_url(), {'biometric_raw': 'valid_scan_data'}, format='json')
    self.assertTrue(KYCProfile.objects.filter(user=self.regular_user).exists())

  def test_biometric_does_not_set_kyc_as_fully_verified(self):
    self.authenticate_as('regular')
    with patch('kyc.services.BiometricService.verify_with_nadra') as mock_nadra:
      mock_nadra.return_value = True
      self.client.post(kyc_biometric_url(), {'biometric_raw': 'valid_scan_data'}, format='json')
    kyc = KYCProfile.objects.get(user=self.regular_user)
    self.assertFalse(kyc.is_verified)