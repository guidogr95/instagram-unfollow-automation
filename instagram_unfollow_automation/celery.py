import os
from celery import Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instagram_unfollow_automation.settings')
app = Celery('instagram_unfollow_automation')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()