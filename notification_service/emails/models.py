from django.db import models
from parent.models import BaseModel

class EmailTemplate(BaseModel):
  TEMPLATE_CHOICES = (
    ('welcome', 'Welcome'),
    ('kyc', 'KYC'),
    ('transaction_completed', 'Transaction Completed'),
    ('refund', 'Refund'),
  )
  name = models.CharField(max_length=100, choices=TEMPLATE_CHOICES, unique=True)
  subject = models.CharField(max_length=200)
  body_html = models.TextField()
  body_text = models.TextField()
    
  class Meta:
    indexes = [models.Index(fields=['name'])]
    
  def __str__(self):
    return self.name

class EmailRecord(BaseModel):
  STATUS_CHOICES = (
    ('sent', 'Sent'),
    ('failed', 'Failed'),
  )
  recipient = models.EmailField()
  template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
  subject = models.CharField(max_length=210)
  body = models.TextField()
  status = models.CharField(max_length=30, choices=STATUS_CHOICES)
  sent_at = models.DateTimeField(auto_now_add=True)
  metadata = models.JSONField(default=dict)
  error_message = models.TextField(blank=True, null=True)
    
  class Meta:
    indexes = [models.Index(fields=['recipient']), models.Index(fields=['status']), models.Index(fields=['sent_at'])]
    ordering = ['-sent_at']
    
  def __str__(self):
    return f'{self.recipient}'