from rest_framework import permissions
from django.conf import settings
from parent.permissions import PakRemitPermission

class InternalServiceGuard(permissions.BasePermission):
  def has_permission(self, request, view):
    token = request.headers.get('X-Internal-Token')
    # print('RECEIVED TOKEN:', repr(token))
    # print('EXPECTED TOKEN:', repr(settings.INTERNAL_SERVICE_SECRET))
    # print('MATCH:', token == settings.INTERNAL_SERVICE_SECRET)
    if token == settings.INTERNAL_SERVICE_SECRET:
      return True
    return False

class WalletAccessPermission(PakRemitPermission):
    pass