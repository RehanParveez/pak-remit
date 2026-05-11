from django.db import models
import uuid
from django.core.exceptions import ValidationError

class RecordEvent(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  event_type = models.CharField(max_length=60, db_index=True)
  aggregate_id = models.UUIDField(db_index=True) 
  aggregate_type = models.CharField(max_length=30) 
  payload = models.JSONField() 
  user_id = models.UUIDField(null=True, blank=True)
  trace_id = models.CharField(max_length=110, null=True, blank=True) 
  created_at = models.DateTimeField(auto_now_add=True, db_index=True)

  class Meta:
    ordering = ['created_at']
    indexes = [models.Index(fields=['aggregate_id', 'created_at']), models.Index(fields=['event_type', 'created_at'])]
        
  def __str__(self):
    return self.event_type

  def save(self, *args, **kwargs):
    if not self._state.adding:
      raise ValidationError('the reco entries cant be changed.')
    super().save(*args, **kwargs)

  def delete(self, *args, **kwargs):
    raise ValidationError('the rec entries cant be deleted.')

class EventProjection(models.Model):
  aggregate_id = models.UUIDField(primary_key=True, editable=False)
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  trace_id = models.CharField(max_length=110, null=True, blank=True)
  aggregate_type = models.CharField(max_length=30)
  current_state = models.JSONField(default=dict)
  last_event_id = models.UUIDField()
  version = models.PositiveIntegerField(default=1)

  def __str__(self):
    return str(self.aggregate_id)