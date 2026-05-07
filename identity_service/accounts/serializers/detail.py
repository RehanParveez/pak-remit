from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from accounts.services import AuthService
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from accounts.models import User, Profile
from django.contrib.auth import authenticate

class ProfileSerializer(serializers.ModelSerializer):
  class Meta:
    model = Profile
    fields = ['full_name', 'dob', 'address', 'city', 'country', 'is_verified', 'risk_score', 'risk_level', 'pic', 'created_at', 'updated_at']
    read_only_fields = ['is_verified', 'risk_score', 'risk_level', 'created_at', 'updated_at']

class UserSerializer(serializers.ModelSerializer):
  password = serializers.CharField(write_only=True, validators=[validate_password])
  password_confirm = serializers.CharField(write_only=True)
  full_name = serializers.CharField(write_only=True)
  cnic = serializers.CharField(write_only=True)

  class Meta:
    model = User
    fields = ['email', 'phone', 'username', 'password', 'password_confirm', 'full_name', 'cnic', 'created_at', 'updated_at']
    read_only_fields = ['created_at', 'updated_at']

  def validate(self, attrs):
    if attrs['password'] != attrs['password_confirm']:
      raise serializers.ValidationError({'password': 'the pass fields did not match.'})
    return attrs

  def create(self, validated_data):
    validated_data.pop('password_confirm')
    return AuthService.register_user(validated_data)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
  @classmethod
  def get_token(cls, user):
    token = super().get_token(user)
    token['user_id'] = str(user.id)
    token['role'] = user.control
    token['is_kyc_verified'] = user.profile.is_verified
    return token

  def validate(self, attrs):
    email = attrs.get('email')
    password = attrs.get('password')
    user = User.objects.filter(email=email).first()
    if user and AuthService.check_account_lockout(user):
      raise serializers.ValidationError('the account is locked, try again')
    auth_user = authenticate(username=email, password=password)
    if not auth_user:
      if user:
        AuthService.increment_failed_login(user)
      raise serializers.ValidationError('wrong credentials.')

    AuthService.reset_failed_login(auth_user)
    request = self.context.get('request')
    AuthService.register_or_update_device(user=auth_user, fingerprint=request.data.get('device_fingerprint', 'web_default'),
      device_type=request.data.get('device_type', 'web'), ip=request.META.get('REMOTE_ADDR'))
    data = super().validate(attrs)
    data['user_id'] = auth_user.id
    data['role'] = auth_user.control
    data['is_kyc_verified'] = auth_user.profile.is_verified
        
    return data