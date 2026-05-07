from django.contrib.auth.models import AbstractUser
from django.db import models
from parent.models import BaseModel

class User(AbstractUser, BaseModel):
  CONTROL_CHOICES = (
    ('user', 'User'),
    ('merchant', 'Merchant'),
    ('agent', 'Agent'),
    ('admin', 'Admin'),
  ) 
  email = models.EmailField(unique=True)
  phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
  cnic_hash = models.CharField(max_length=65, unique=True, null=True, blank=True)
  control = models.CharField(max_length=25, choices=CONTROL_CHOICES, default = 'user')
  failed_login_attempts = models.PositiveIntegerField(default=0)
  acc_locked_until = models.DateTimeField(null=True, blank=True)
  last_pass_change = models.DateTimeField(auto_now_add=True, null=True)
  is_deleted = models.BooleanField(default=False)

  USERNAME_FIELD = 'email'
  REQUIRED_FIELDS = ['username', 'phone']

  class Meta:
    indexes = [models.Index(fields=['email', 'phone'])]

  def __str__(self):
    return f'{self.email}'

class Profile(BaseModel):
  RISK_LEVELS = (
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
  )
  user = models.OneToOneField(User, on_delete=models.CASCADE, related_name = 'profile')
  full_name = models.CharField(max_length=100, null=True, blank=True)
  dob = models.DateField(null=True, blank=True)
  address = models.CharField(max_length=270, null=True, blank=True)
  city = models.CharField(max_length=55, null=True, blank=True)
  country = models.CharField(max_length=55, default = 'Pakistan')
  is_verified = models.BooleanField(default=False)
  risk_score = models.IntegerField(default=0)
  risk_level = models.CharField(max_length=14, choices=RISK_LEVELS, default = 'low')
  pic = models.ImageField(upload_to = 'profiles/', null=True, blank=True)

  def __str__(self):
    return f'{self.user.email}'

class UserDevice(BaseModel):
  TYPES = (
    ('ios', 'IOS'),
    ('android', 'Android'),
    ('web', 'Web'),
  )
  user = models.ForeignKey(User, on_delete=models.CASCADE, related_name = 'devices')
  device_fingerprint = models.CharField(max_length=270)
  type = models.CharField(max_length=14, choices=TYPES, default = 'web')
  is_trusted = models.BooleanField(default=False)
  last_login = models.DateTimeField(auto_now=True)
  last_ip = models.GenericIPAddressField(null=True, blank=True)

  class Meta:
    unique_together = ('user', 'device_fingerprint')

  def __str__(self):
    return f'{self.type}'