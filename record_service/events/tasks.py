from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from events.models import EventProjection, RecordEvent
from events.services import ProjectionBuilder
from django.utils import timezone
from dateutil.relativedelta import relativedelta

@shared_task
def send_email(subject, message):
  send_mail(subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[settings.EMAIL_HOST_USER],
    fail_silently=False)

@shared_task
def rebuild_all_projections():
  projections = EventProjection.objects.using(None).all()
  count = projections.count()
  for proj in projections:
    ProjectionBuilder.rebuild_projection(proj.aggregate_id)
  msg = f'{count} projections {timezone.now()}'
  send_email.delay('weekly rebuild', msg)
    
  return msg

@shared_task
def archive_old_events():
  cutoff_date = timezone.now() - relativedelta(years=1)
  old_events = RecordEvent.objects.using(None).filter(created_at__lt=cutoff_date)
  count = old_events.count()
  msg = f'{count} old events.'
  send_email.delay('monthly archive', msg)
  return msg