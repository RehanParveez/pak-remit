import uuid
from django.db import models

class BaseModel(models.Model):
  id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  trace_id = models.CharField(max_length=110, null=True, blank=True)

  class Meta:
    abstract = True