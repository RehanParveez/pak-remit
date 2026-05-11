import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'record_center.settings')

app = Celery('record_center')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()