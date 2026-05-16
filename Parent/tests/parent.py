from rest_framework.test import APITestCase, APIClient, APIRequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class ParentTestCase(APITestCase):
  @classmethod
  def setUpTestData(cls):
    cls.regular_user = User.objects.create_user(username = 'user1', email = 'user1@pakremit.com', phone = '03007634561',
      password = 'user112312', control = 'user')
    cls.verified_user = User.objects.create_user(username = 'user2', email = 'user2@pakremit.com', phone = '0300654562',
      password = 'user2', control='user')
    cls.merchant = User.objects.create_user(username = 'merchant', email = 'merchant@gmail.com', phone = '03009934563',
      password = 'mer12312', control = 'merchant')
    cls.agent = User.objects.create_user(username = 'agent', email = 'agent@pakremit.com', phone = '03005644564', password = 'agent12312',
      control = 'agent')
    cls.admin = User.objects.create_user(
      username = 'admin', email = 'admin@pakremit.com', phone = '03121564565', password = 'adm12312', control = 'admin', is_staff=True)
    cls.staff_user = User.objects.create_user(
      username = 'staff_user', email = 'staff@pakremit.com', phone = '03148764566', password = 'staff12312', control = 'user', is_staff=True)
    cls.expired_kyc_user = User.objects.create_user(username = 'expired_kyc', email = 'expired@pakremit.com', phone='03151684534',
      password = 'exp12312', control = 'user')
    cls.pending_kyc_user = User.objects.create_user(username = 'pending_kyc', email = 'pending@pakremit.com', phone = '0317744561',
      password = 'pen12312', control = 'user')

  def setUp(self):
    self.client = APIClient()
    self.factory = APIRequestFactory()

  def _build_token(self, user: AbstractUser, is_kyc_verified: bool) -> str:
    refresh = RefreshToken.for_user(user)
    refresh['user_id'] = str(user.pk)
    refresh['email'] = user.email
    refresh['control'] = user.control
    refresh['is_staff'] = user.is_staff
    refresh['is_kyc_verified'] = is_kyc_verified
    return str(refresh.access_token)

  def get_regular_user_token(self) -> str:
    return self._build_token(self.regular_user, is_kyc_verified=False)

  def get_verified_user_token(self) -> str:
    return self._build_token(self.verified_user, is_kyc_verified=True)

  def get_merchant_token(self) -> str:
    return self._build_token(self.merchant, is_kyc_verified=True)

  def get_agent_token(self) -> str:
    return self._build_token(self.agent, is_kyc_verified=True)

  def get_admin_token(self) -> str:
    return self._build_token(self.admin, is_kyc_verified=False)

  def get_staff_token(self) -> str:
    return self._build_token(self.staff_user, is_kyc_verified=False)

  def get_expired_kyc_token(self) -> str:
    return self._build_token(self.expired_kyc_user, is_kyc_verified=False)

  def get_pending_kyc_token(self) -> str:
    return self._build_token(self.pending_kyc_user, is_kyc_verified=False)

  def get_custom_token(self, user: AbstractUser, is_kyc_verified: bool) -> str:
    return self._build_token(user, is_kyc_verified=is_kyc_verified)

  def authenticate_as(self, user_type: str = 'verified') -> None:
    token_builders = {'regular': self.get_regular_user_token, 'verified': self.get_verified_user_token, 'merchant': self.get_merchant_token,
      'agent': self.get_agent_token, 'admin': self.get_admin_token, 'staff': self.get_staff_token, 'expired': self.get_expired_kyc_token,
        'pending': self.get_pending_kyc_token}
    if user_type not in token_builders:
      raise ValueError(f'Unknown user_type {user_type!r}. Valid options: {sorted(token_builders.keys())}')
    self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_builders[user_type]()}')

  def clear_authentication(self) -> None:
    self.client.credentials()

  def authenticate_as_internal_service(self) -> None:
    self.client.credentials(HTTP_X_INTERNAL_TOKEN=settings.INTERNAL_SERVICE_SECRET)

  def authenticate_as_record_service(self) -> None:
    self.client.credentials(HTTP_X_INTERNAL_SERVICE_KEY=settings.INTERNAL_SERVICE_SECRET)

  def make_auth_dict(self, user: AbstractUser, is_kyc_verified: bool = True, control: str = None, is_staff: bool = None) -> dict:
    auth_control = control
    if auth_control is None: auth_control = user.control
    auth_staff = is_staff
    if auth_staff is None: auth_staff = user.is_staff
    return {'user_id': str(user.pk), 'email': user.email, 'control': auth_control, 'is_staff': auth_staff, 'is_kyc_verified': is_kyc_verified}
  
  def test_auth_setup(self) -> None:
    self.assertEqual(self.regular_user.username, 'user1')
    self.assertEqual(self.verified_user.username, 'user2')
    self.assertEqual(self.merchant.username, 'merchant')
    self.assertEqual(self.agent.username, 'agent')
    self.assertEqual(self.admin.username, 'admin')
    self.assertEqual(self.staff_user.username, 'staff_user')
    self.assertEqual(self.expired_kyc_user.username, 'expired_kyc')
    self.assertEqual(self.pending_kyc_user.username, 'pending_kyc')
    
# class IdentityServiceTestCase(ParentTestCase):
#     @classmethod
#     def setUpTestData(cls):
#       from kyc.models import KYCProfile
#       super().setUpTestData()
#       cls.verified_kyc = KYCProfile.objects.create(user=cls.verified_user, status = 'approved', tier = 'tier2', is_verified=True,
#         verified_at=timezone.now(), expires_at=timezone.now() + timedelta(days=40))
#       cls.merchant_kyc = KYCProfile.objects.create(user=cls.merchant, status = 'approved', tier = 'tier3', is_verified=True,
#         verified_at=timezone.now(), expires_at=timezone.now() + timedelta(days=50))
#       cls.agent_kyc = KYCProfile.objects.create(user=cls.agent, status = 'approved', tier = 'tier2', is_verified=True, verified_at=timezone.now(),
#         expires_at=timezone.now() + timedelta(days=60))
#       cls.expired_kyc = KYCProfile.objects.create(user=cls.expired_kyc_user, status = 'expired', tier = 'tier1', is_verified=False, verified_at=timezone.now() - timedelta(days=20),
#         expires_at=timezone.now() - timedelta(days=70))
#       cls.pending_kyc = KYCProfile.objects.create(user=cls.pending_kyc_user, status = 'pending', tier = 'tier1', is_verified=False)