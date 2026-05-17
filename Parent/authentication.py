from rest_framework_simplejwt.authentication import JWTTokenUserAuthentication

print('authentication.py module loaded')
class ServiceJWTAuthentication(JWTTokenUserAuthentication):
  def authenticate(self, request):
    print('ServiceJWTAuthentication running')
    result = super().authenticate(request)
    if result is None:
      return None
    user, token = result
    request._auth = token
    return (user, token)