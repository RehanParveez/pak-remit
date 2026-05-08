from rest_framework import permissions

class AdminPermission(permissions.BasePermission):
  def has_permission(self, request, view):
    user = request.user
    if not user:
      return False
    if not user.is_authenticated:
      return False
    if user.is_staff:
      return True
    user_control = getattr(user, 'control', None)
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
    if not hasattr(user, 'kyc_profile'):
      return False
    if user.kyc_profile.is_verified:
      return True

    return False