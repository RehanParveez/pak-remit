from django.conf import settings
import hashlib
from django.db import transaction
from accounts.models import User, Profile, UserDevice
from django.utils import timezone
from datetime import timedelta

class AuthService: 
  @staticmethod
  def hash_cnic(cnic):
    salt = getattr(settings, 'CNIC_SALT', 'pak_remit_secure_salt_2026')
    hash_obj = hashlib.sha256(f"{cnic}{salt}".encode())
    return hash_obj.hexdigest()

  @staticmethod
  def register_user(validated_data):
    full_name = validated_data.pop('full_name', '')
    cnic = validated_data.pop('cnic', '')
    with transaction.atomic():
      user = User.objects.create_user(**validated_data, cnic_hash=AuthService.hash_cnic(cnic))
      Profile.objects.create(user=user, full_name=full_name, risk_score=0, risk_level = 'low', is_verified=False)
      return user

  @staticmethod
  def check_account_lockout(user):
    if not user.acc_locked_until:
      return False  
    current_time = timezone.now()
    if current_time < user.acc_locked_until:
      return True  
    return False

  @staticmethod
  def increment_failed_login(user):
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= 5:
      user.acc_locked_until = timezone.now() + timedelta(minutes=30)
      user.failed_login_attempts = 0 
    user.save()

  @staticmethod
  def reset_failed_login(user):
    if user.failed_login_attempts > 0:
      user.failed_login_attempts = 0
      user.save()

  @staticmethod
  def register_or_update_device(user, fingerprint, device_type, ip):
    device, created = UserDevice.objects.update_or_create(user=user, device_fingerprint=fingerprint,
      defaults={'type': device_type, 'last_ip': ip, 'last_login': timezone.now()})
    return device

  @staticmethod
  def update_password(user, new_password):
    user.set_password(new_password)
    user.last_pass_change = timezone.now()
    user.save()