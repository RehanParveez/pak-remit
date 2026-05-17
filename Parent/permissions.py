from rest_framework import permissions

class PakRemitPermission(permissions.BasePermission):
  def _get_auth(self, request):
    if request.auth:
      return request.auth
    if request.user and hasattr(request.user, 'token'):
      return request.user.token
    return None
  def has_permission(self, request, view):
    auth = self._get_auth(request)
    if not auth:
      return False
    user_control = auth.get('control')
    is_staff = auth.get('is_staff', False)
    is_verified = auth.get('is_kyc_verified', False)
    if user_control == 'admin':
      return True
    if is_staff:
      return True
    if not is_verified:
      return False

    allowed_control = ['user', 'merchant', 'agent']
    if user_control in allowed_control:
      return True     
    return False

  def has_object_permission(self, request, view, obj):
    auth = self._get_auth(request)
    if not auth:
      return False
    requesting_user_id = str(auth.get('user_id'))
    user_control = auth.get('control')

    if user_control == 'admin':
      return True
    if hasattr(obj, 'email') and hasattr(obj, 'id'):
      return str(obj.id) == requesting_user_id
    if hasattr(obj, 'user'):
      obj_owner_id = getattr(obj.user, 'id', obj.user)
      return str(obj_owner_id) == requesting_user_id
    if hasattr(obj, 'wallet'):
      return str(obj.wallet.user_id) == requesting_user_id
    for field in ['user_id', 'owner_id', 'customer_id']:
      if hasattr(obj, field):
        return str(getattr(obj, field)) == requesting_user_id
            
    return False