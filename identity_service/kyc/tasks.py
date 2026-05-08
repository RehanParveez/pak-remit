from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from kyc.models import KYCProfile
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def check_kyc_expiry():
  today = timezone.now()
  thirty_days_later = today + timedelta(days=30)
  upc_expiries = KYCProfile.objects.filter(expires_at__date=thirty_days_later.date(), is_verified=True,
  status = 'approved')
    
  for profile in upc_expiries:
    subject = 'the KYC will exp in 30 days'
    message = f'the KYC will exp on {profile.expires_at.date()}'
    send_mail(subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[profile.user.email],
      fail_silently=True)
  return f'notified {upc_expiries.count()} users'

@shared_task
def expire_old_kycs():
  now = timezone.now()
  expired_profiles = KYCProfile.objects.filter(expires_at__lt=now, is_verified=True)
  count = 0
  for profile in expired_profiles:
    profile.status = 'expired'
    profile.is_verified = False
    profile.save()
    subject = 'the KYC has expired'
    message = 'friend kindly re submit your docs'
        
    send_mail(subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[profile.user.email],
      fail_silently=True)
    count += 1
    
  return f'expired {count} users'