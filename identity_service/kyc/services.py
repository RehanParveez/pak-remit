import hashlib
import time
import random
from django.db import transaction
from kyc.models import KYCProfile, VerificationLog
from django.utils import timezone
from datetime import timedelta

class BiometricService:
  @staticmethod
  def hash_biometric_data(raw_data: str) -> str:
    return hashlib.sha256(raw_data.encode()).hexdigest()

  @staticmethod
  def verify_with_nadra(biometric_hash: str) -> bool:
    if not biometric_hash:
      return False
    time.sleep(1)  
    return random.random() < 0.90

class KYCService:
  @staticmethod
  @transaction.atomic
  def submit_kyc(user, cnic_front, cnic_back, utility_bill=None):
    kyc_profile, created = KYCProfile.objects.update_or_create(user=user,
      defaults={'cnic_front_image': cnic_front, 'cnic_back_image': cnic_back, 'utility_bill_image': utility_bill,
        'status': 'pending', 'is_verified': False})
    VerificationLog.objects.create(kyc_profile=kyc_profile, method = 'cnic', status = 'submitted',
      metadata = {'info': 'the user upl KYC docs for analyze'})
    return kyc_profile

  @staticmethod
  @transaction.atomic
  def approve_kyc(kyc_profile, admin_user, tier = 'tier1'):
    kyc_profile.status = 'approved'
    kyc_profile.is_verified = True
    kyc_profile.tier = tier
    kyc_profile.verified_by = admin_user
    kyc_profile.verified_at = timezone.now()
    kyc_profile.expires_at = timezone.now() + timedelta(days=30) 
    kyc_profile.save()
    VerificationLog.objects.create(kyc_profile=kyc_profile,
      method = 'manual', status = 'approved', verified_by=admin_user, metadata={'tier_assigned': tier})
    return kyc_profile

  @staticmethod
  @transaction.atomic
  def reject_kyc(kyc_profile, reason, admin_user):
    kyc_profile.status = 'rejected'
    kyc_profile.is_verified = False
    kyc_profile.rej_reason = reason
    kyc_profile.save()
    VerificationLog.objects.create(kyc_profile=kyc_profile, method = 'manual', status = 'rejected',
      verified_by=admin_user, metadata = {'reason': reason})
    return kyc_profile