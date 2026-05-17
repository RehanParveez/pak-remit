from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from accounts.serializers.detail import UserSerializer, UserSerializer, CustomTokenObtainPairSerializer
from accounts.models import User
from accounts.serializers.detail import UpdatePasswordSerializer
from accounts.services import AuthService

class AuthViewSet(viewsets.GenericViewSet):
  permission_classes = [permissions.AllowAny]
  serializer_class = UserSerializer

  @action(detail=False, methods=['post'])
  def register(self, request):
    serializer = self.get_serializer(data=request.data)
    if serializer.is_valid():
      user = serializer.save()
      return Response({'status': 'success', 'message': 'the user is registered', 'data': {'user_id': user.id}}, status=201)  
    return Response(serializer.errors, status=400)

class CustomTokenObtainPairView(TokenObtainPairView):
  serializer_class = CustomTokenObtainPairSerializer

class UserViewSet(viewsets.GenericViewSet):
  queryset = User.objects.all()
  permission_classes = [permissions.IsAuthenticated]
  serializer_class = UserSerializer
  
  def get_queryset(self):
    return self.queryset.filter(id=self.request.user.id)

  @action(detail=False, methods=['get'])
  def profile(self, request):
    serializer = self.get_serializer(request.user)
    return Response(serializer.data)
  
  @action(detail=False, methods=['patch'])
  def update_password(self, request):
    serializer = UpdatePasswordSerializer(data=request.data, user=request.user)
    if serializer.is_valid():
      AuthService.update_password(request.user, serializer.validated_data['new_password'])
      return Response({'message': 'the password is upd'}, status=200)
    return Response(serializer.errors, status=400)