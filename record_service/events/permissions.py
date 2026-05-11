from rest_framework import permissions
from django.conf import settings

class InternalServiceGuard(permissions.BasePermission):
  def has_permission(self, request, view):
    service_key = request.headers.get('X-Internal-Service-Key')
    return service_key == settings.INTERNAL_SERVICE_SECRET

class ViewEventsPerm(permissions.BasePermission):
  def has_permission(self, request, view):
    if not request.auth:
      return False
    return True

  def has_object_permission(self, request, view, obj):
    user_control = request.auth.get('control')
    if user_control == 'admin':
      return True
    requesting_user_id = str(request.auth.get('user_id'))
    return str(obj.user_id) == requesting_user_id