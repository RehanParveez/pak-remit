from django.db import models
from parent.models import BaseModel
import secrets

class WebhookEndpoint(BaseModel):
  merchant_id = models.UUIDField()
  url = models.URLField(max_length=500)
  events = models.JSONField(default=list)
  secret = models.CharField(max_length=110, blank=True)
  is_active = models.BooleanField(default=True)
    
  class Meta:
    indexes = [models.Index(fields=['merchant_id']), models.Index(fields=['is_active'])]
    
  def save(self, *args, **kwargs):
    if not self.secret:
      self.secret = secrets.token_urlsafe(32)
    super().save(*args, **kwargs)
    
  def __str__(self):
    return f'{self.merchant_id} - {self.url}'

class WebhookDelivery(BaseModel):
  STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('sent', 'Sent'),
    ('failed', 'Failed'),
  )
  endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
  event_type = models.CharField(max_length=100)
  payload = models.JSONField()
  status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
  attempts = models.IntegerField(default=0)
  next_retry_at = models.DateTimeField(null=True, blank=True)
  response_code = models.IntegerField(null=True, blank=True)
  response_body = models.TextField(blank=True, null=True)
    
  class Meta:
    indexes = [models.Index(fields=['status', 'next_retry_at']), models.Index(fields=['event_type']), models.Index(fields=['created_at'])]
    ordering = ['-created_at']
    
  def __str__(self):
    return f'{self.event_type} - {self.status}'