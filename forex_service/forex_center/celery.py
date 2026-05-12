import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forex_center.settings')

app = Celery('forex_center')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()