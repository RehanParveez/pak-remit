from parent.tests.parent import ParentTestCase
from kyc.models import KYCProfile
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from parent.permissions import PakRemitPermission
from kyc.permissions import AdminPermission, KYCVerifiedPermission
from django.contrib.auth.models import AnonymousUser

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

class PakRemitHasPermissionTests(IdentityServiceTestCase):

  def setUp(self):
    super().setUp()
    self.perm = PakRemitPermission()

  def test_denies_when_request_auth_is_none(self):
    request = make_request()
    request.auth = None
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_unverified_regular_user(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.regular_user, is_kyc_verified=False)
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_expired_kyc_user(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.expired_kyc_user, is_kyc_verified=False)
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_pending_kyc_user(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.pending_kyc_user, is_kyc_verified=False)
    self.assertFalse(self.perm.has_permission(request, view))

  def test_allows_kyc_verified_user(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.verified_user, is_kyc_verified=True)
    self.assertTrue(self.perm.has_permission(request, view))

  def test_allows_kyc_verified_merchant(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.merchant, is_kyc_verified=True)
    self.assertTrue(self.perm.has_permission(request, view))

  def test_allows_kyc_verified_agent(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.agent, is_kyc_verified=True)
    self.assertTrue(self.perm.has_permission(request, view))

  def test_allows_admin_without_kyc(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.admin, is_kyc_verified=False)
    self.assertTrue(self.perm.has_permission(request, view))

  def test_allows_staff_without_kyc(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.staff_user, is_kyc_verified=False)
    self.assertTrue(self.perm.has_permission(request, view))

  def test_denies_unknown_control_even_if_kyc_verified(self):
    request = make_request()
    request.auth = {'user_id': str(self.verified_user.pk), 'control': 'unknown_role', 'is_staff': False, 'is_kyc_verified': True}
    self.assertFalse(self.perm.has_permission(request, view))

class PakRemitHasObjectPermTests(IdentityServiceTestCase):

  def setUp(self):
    super().setUp()
    self.perm = PakRemitPermission()

  def _make_obj(self, **kwargs):
    class Obj:
      pass
    o = Obj()
    for k, v in kwargs.items():
      setattr(o, k, v)
    return o

  def test_denies_when_auth_is_none(self):
    request = make_request()
    request.auth = None
    obj = self._make_obj(user_id=str(self.verified_user.pk))
    self.assertFalse(self.perm.has_object_permission(request, view, obj))

  def test_admin_can_access_any_object(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.admin, control = 'admin')
    obj = self._make_obj(user_id=str(self.verified_user.pk))
    self.assertTrue(self.perm.has_object_permission(request, view, obj))

  def test_user_can_access_own_user_object(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.verified_user)
    self.assertTrue(self.perm.has_object_permission(request, view, self.verified_user))

  def test_user_cannot_access_another_users_object(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.verified_user)
    self.assertFalse(self.perm.has_object_permission(request, view, self.merchant))

  def test_ownership_via_user_fk_object(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.verified_user)
    inner = type('U', (), {'id': self.verified_user.pk})()
    obj = self._make_obj(user=inner)
    self.assertTrue(self.perm.has_object_permission(request, view, obj))

  def test_ownership_via_user_fk_raw_id(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.verified_user)
    obj = self._make_obj(user=self.verified_user.pk)
    self.assertTrue(self.perm.has_object_permission(request, view, obj))

  def test_ownership_via_user_id_field(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.verified_user)
    obj = self._make_obj(user_id=self.verified_user.pk)
    self.assertTrue(self.perm.has_object_permission(request, view, obj))

  def test_ownership_via_owner_id_field(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.verified_user)
    obj = self._make_obj(owner_id=self.verified_user.pk)
    self.assertTrue(self.perm.has_object_permission(request, view, obj))

  def test_ownership_via_customer_id_field(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.verified_user)
    obj = self._make_obj(customer_id=self.verified_user.pk)
    self.assertTrue(self.perm.has_object_permission(request, view, obj))

  def test_denies_when_no_ownership_field_present(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.verified_user)
    obj = self._make_obj(amount=500, currency = 'pkr')
    self.assertFalse(self.perm.has_object_permission(request, view, obj))

  def test_wrong_owner_via_user_id_field_denied(self):
    request = make_request()
    request.auth = self.make_auth_dict(self.verified_user)
    obj = self._make_obj(user_id=self.merchant.pk)
    self.assertFalse(self.perm.has_object_permission(request, view, obj))

class AdminPermission_Tests(IdentityServiceTestCase):

  def setUp(self):
    super().setUp()
    self.perm = AdminPermission()

  def _req(self, user, control=None, is_staff=None):
    request = make_request(method = 'post')
    request.user = user
    request.auth = self.make_auth_dict(user, control=control, is_staff=is_staff)
    return request

  def test_denies_when_user_is_none(self):
    request = make_request()
    request.user = None
    request.auth = {}
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_unauthenticated_user(self):
    request = make_request()
    request.user = AnonymousUser()
    request.auth = {}
    self.assertFalse(self.perm.has_permission(request, view))

  def test_allows_admin_control(self):
    request = self._req(self.admin, control = 'admin')
    self.assertTrue(self.perm.has_permission(request, view))

  def test_allows_is_staff_true(self):
    request = self._req(self.staff_user, is_staff=True)
    self.assertTrue(self.perm.has_permission(request, view))

  def test_denies_verified_regular_user(self):
    request = self._req(self.verified_user)
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_merchant(self):
    request = self._req(self.merchant)
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_agent(self):
    request = self._req(self.agent)
    self.assertFalse(self.perm.has_permission(request, view))

class KYCVerifiedPermTests(IdentityServiceTestCase):
  def setUp(self):
    super().setUp()
    self.perm = KYCVerifiedPermission()

  def test_denies_when_user_is_none(self):
    request = make_request()
    request.user = None
    self.assertFalse(self.perm.has_permission(request, view))

  def test_denies_unauthenticated_user(self):
    request = make_request()
    request.user = AnonymousUser()
    request.auth = {}
    self.assertFalse(self.perm.has_permission(request, view))

  def test_allows_verified_user(self):
    request = make_request()
    request.user = self.verified_user
    request.auth = self.make_auth_dict(self.verified_user, is_kyc_verified=True)
    self.assertTrue(self.perm.has_permission(request, view))

  def test_denies_unverified_user(self):
    request = make_request()
    request.user = self.regular_user
    request.auth = {'user_id': str(self.regular_user.pk), 'is_kyc_verified': False}
    self.assertFalse(self.perm.has_permission(request, view))