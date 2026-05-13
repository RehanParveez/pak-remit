from rest_framework import serializers
from emails.models import EmailTemplate, EmailRecord

class EmailTemplateSerializer(serializers.ModelSerializer):
  class Meta:
    model = EmailTemplate
    fields = ['id', 'name', 'subject', 'body_html', 'body_text', 'created_at']
    read_only_fields = ['id', 'created_at']


class EmailLogSerializer(serializers.ModelSerializer):
  template_name = serializers.CharField(source='template.name', read_only=True)
  class Meta:
    model = EmailRecord
    fields = ['id', 'recipient', 'template', 'template_name', 'subject', 'status', 'sent_at', 'metadata', 'error_message']
    read_only_fields = ['id', 'sent_at']