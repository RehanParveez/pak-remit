from django.db import models
from django.conf import settings
from parent.models import BaseModel

class KYCProfile(BaseModel):
  STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('analyzed', 'Analyzed'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('expired', 'Expired'),
  )
    
  TIER_CHOICES = (
    ('tier1', 'Tier1'),
    ('tier2', 'Tier2'),
    ('tier3', 'Tier3'),
  )
  user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name = 'kyc_profile')
  status = models.CharField(max_length=25, choices=STATUS_CHOICES, default = 'pending')
  tier = models.CharField(max_length=25, choices=TIER_CHOICES, default = 'tier1')
  cnic_front_image = models.ImageField(upload_to = 'kyc/cnic/', null=True, blank=True)
  cnic_back_image = models.ImageField(upload_to = 'kyc/cnic/', null=True, blank=True)
  utility_bill_image = models.ImageField(upload_to = 'kyc/bills/', null=True, blank=True)
  biometric_hash = models.CharField(max_length=270, null=True, blank=True)
  is_biometric_verified = models.BooleanField(default=False)
  is_verified = models.BooleanField(default=False)
  verified_at = models.DateTimeField(null=True, blank=True)
  verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, 
    related_name = 'verifications_performed')
  expires_at = models.DateTimeField(null=True, blank=True)
  rej_reason = models.TextField(null=True, blank=True)

  class Meta:
    indexes = [models.Index(fields=['status', 'is_verified']), models.Index(fields=['user', 'is_verified'])]

  def __str__(self):
    return f'{self.user.email}'

class VerificationLog(BaseModel):
  METHODS = (
    ('cnic', 'CNIC'),
    ('biometric', 'Biometric'),
    ('manual', 'Manual'),
    ('nadra', 'NADRA'),
  )
  kyc_profile = models.ForeignKey(KYCProfile, on_delete=models.CASCADE, related_name = 'records')
  method = models.CharField(max_length=30, choices=METHODS)
  status = models.CharField(max_length=55)
  metadata = models.JSONField(default=dict)
  verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

  class Meta:
    ordering = ['-created_at']