
from celery import Celery
from django.core.mail import send_mail


app = Celery('celery_tasks.tasks', broker='redis://192.168.12.191/2')


import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh2.settings")
django.setup()

@app.task
def task_send_mail(subject, message,sender,receiver,html_message):
    print('start...')
    send_mail(subject, message, sender, receiver, html_message=html_message)
    print('end...')