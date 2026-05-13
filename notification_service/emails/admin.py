from django.contrib import admin
from .models import EmailTemplate, EmailRecord

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
  list_display = ['name', 'subject', 'body_html', 'body_text']
  list_filter = ('name',)
  search_fields = ('name', 'subject')

@admin.register(EmailRecord)
class EmailRecordAdmin(admin.ModelAdmin):
  list_display = ('recipient', 'template', 'subject', 'body', 'status', 'sent_at', 'metadata', 'error_message')
  list_filter = ('status', 'sent_at', 'template')
  search_fields = ('recipient', 'subject', 'error_message')
  readonly_fields = ('sent_at', 'body', 'metadata', 'error_message')