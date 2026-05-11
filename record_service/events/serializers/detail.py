from rest_framework import serializers
from events.models import RecordEvent, EventProjection

class RecordEventSerializer(serializers.ModelSerializer):
  class Meta:
    model = RecordEvent
    fields = ['id', 'event_type', 'aggregate_id', 'aggregate_type', 'payload', 'user_id', 'trace_id', 'created_at']
    read_only_fields = ['id', 'event_type', 'aggregate_id', 'aggregate_type', 'payload', 'user_id', 'trace_id', 'created_at']

class EventProjectionSerializer(serializers.ModelSerializer):
  class Meta:
    model = EventProjection
    read_only_fields = ['aggregate_id', 'created_at', 'updated_at', 'aggregate_type', 'current_state', 'last_event_id', 'version']