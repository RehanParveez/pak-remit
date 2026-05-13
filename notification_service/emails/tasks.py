from celery import shared_task
from emails.services import EmailService
from django.core.mail import send_mail
from django.conf import settings

@shared_task(name='emails.tasks.send_transaction_notification')
def send_transaction_notification(transaction_id, sender_email, receiver_email):
  context = {'transaction_id': transaction_id}
  EmailService.send_email(recipient=sender_email, template_name = 'transaction_completed', context=context)
  EmailService.send_email(recipient=receiver_email, template_name = 'transaction_completed', context=context)
  subject = f'trans notif sent {transaction_id}'
  message = f'''
trans notifi emails sent.

transaction id: {transaction_id}
sender: {sender_email}
receiver: {receiver_email}

    '''
    
  send_mail(subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=['rehanrural@gmail.com'],
    fail_silently=False)
    
  return True