import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_center.settings')

app = Celery('notification_center')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()