from rest_framework import serializers

class EventAppendSerializer(serializers.Serializer):
  event_type = serializers.CharField(max_length=60)
  aggregate_id = serializers.UUIDField()
  aggregate_type = serializers.ChoiceField(choices=['wallet', 'transaction'])
  payload = serializers.JSONField()
  user_id = serializers.UUIDField(required=False, allow_null=True)
  trace_id = serializers.CharField(max_length=110, required=False, allow_null=True)

class EventReplaySerializer(serializers.Serializer):
  aggregate_id = serializers.UUIDField()