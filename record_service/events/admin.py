from django.contrib import admin
from events.models import RecordEvent, EventProjection

@admin.register(RecordEvent)
class RecordEventAdmin(admin.ModelAdmin):
  list_display = ['id', 'event_type', 'aggregate_id', 'aggregate_type', 'payload', 'user_id', 'trace_id', 'created_at']

@admin.register(EventProjection)
class EventProjectionAdmin(admin.ModelAdmin):
  list_display = ['aggregate_id', 'created_at', 'updated_at', 'trace_id', 'aggregate_type', 'current_state', 'last_event_id', 'version']