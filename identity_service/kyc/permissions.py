from rest_framework import permissions

class AdminPermission(permissions.BasePermission):
  def has_permission(self, request, view):
    user = request.user
    if not user:
      return False
    if not user.is_authenticated:
      return False
    if request.auth.get('is_staff'):
      return True
    user_control = request.auth.get('control')
    if user_control == 'admin':
      return True

    return False

class KYCVerifiedPermission(permissions.BasePermission):
  def has_permission(self, request, view):
    user = request.user
    if not user:
      return False
    if not user.is_authenticated:
      return False
    if request.auth.get('is_verified'):
      return True

    return False