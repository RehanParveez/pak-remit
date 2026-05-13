from rest_framework import serializers

class SendEmailSerializer(serializers.Serializer):
  recipient = serializers.EmailField()
  template_name = serializers.CharField(max_length=110)
  context = serializers.JSONField()