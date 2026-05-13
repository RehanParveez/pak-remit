from emails.models import EmailTemplate, EmailRecord
from django.core.mail import send_mail
from django.template import Context, Template
from django.conf import settings
import uuid

class EmailService:
  @staticmethod
  def send_email(recipient, template_name, context):
    template = EmailTemplate.objects.get(name=template_name)
    ctx = Context(context)
    subject = Template(template.subject).render(ctx)
    body_text = Template(template.body_text).render(ctx)
    body_html = Template(template.body_html).render(ctx)
        
    send_mail(subject=subject, message=body_text, from_email=settings.EMAIL_HOST_USER, recipient_list=[recipient], fail_silently=False, 
      html_message=body_html)
    EmailRecord.objects.create(recipient=recipient, template=template, subject=subject, body=body_text, status = 'sent', 
      metadata=context, trace_id = f'email-{uuid.uuid4().hex[:8]}')
    return True

  @staticmethod
  def send_bulk_emails(recipients, template_name, context):
    sent_count = 0
    for recipient in recipients:
      EmailService.send_email(recipient, template_name, context)
      sent_count += 1
    return sent_count