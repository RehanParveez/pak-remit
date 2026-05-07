from rest_framework import serializers
from accounts.models import Profile, User

class ProfileSerializer(serializers.ModelSerializer):
  class Meta:
    model = Profile
    fields = ['full_name', 'dob', 'address', 'city', 'country']

class UserSerializer1(serializers.ModelSerializer):
  profile = ProfileSerializer(read_only=True)
  class Meta:
    model = User
    fields = ['id', 'email', 'phone', 'username', 'control', 'profile', 'created_at']
    read_only_fields = ['id', 'control', 'created_at']