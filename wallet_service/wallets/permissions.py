from rest_framework import permissions
from django.conf import settings
from parent.permissions import PakRemitPermission

class InternalServiceGuard(permissions.BasePermission):
  def has_permission(self, request, view):
    token = request.headers.get('X-Internal-Token')
    if token == settings.INTERNAL_SERVICE_SECRET:
      return True
    return False

class WalletAccessPermission(PakRemitPermission):
    pass