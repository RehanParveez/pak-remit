from rest_framework import viewsets, permissions
from kyc.models import KYCProfile
from kyc.permissions import AdminPermission
from parent.permissions import PakRemitPermission
from rest_framework.decorators import action
from kyc.serializers.basic import KYCSerializer1
from kyc.serializers.detail import KYCDetailSerializer
from kyc.services import KYCService, BiometricService
from rest_framework.response import Response

class KYCViewSet(viewsets.ModelViewSet):
  queryset = KYCProfile.objects.all()

  def get_permissions(self):
    if self.action == 'approve':
      return [AdminPermission()]
    if self.action == 'reject':
      return [AdminPermission()]
    if self.action == 'list':
      return [AdminPermission()]
    if self.action == 'submit':
      return [permissions.IsAuthenticated()]
    if self.action == 'verify_biometric':
      return [permissions.IsAuthenticated()]
    return [PakRemitPermission()]

  def get_serializer_class(self):
    if self.action == 'submit':
      return KYCSerializer1
    return KYCDetailSerializer

  def get_queryset(self):
    user = self.request.user
    auth_data = self.request.auth
    if user.is_staff:
      return self.queryset
    user_control = auth_data.get('control')
    if user_control == 'admin':
      return self.queryset
    return self.queryset.filter(user=user)

  @action(detail=False, methods=['post'])
  def submit(self, request):
    serializer = self.get_serializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    profile = KYCService.submit_kyc(user=request.user, cnic_front=serializer.validated_data.get('cnic_front_image'),
      cnic_back=serializer.validated_data.get('cnic_back_image'), utility_bill=serializer.validated_data.get('utility_bill_image'))
    response_serializer = KYCDetailSerializer(profile)
    return Response(response_serializer.data, status=201)

  @action(detail=True, methods=['post'])
  def approve(self, request, pk=None):
    profile = self.get_object()
    target_tier = request.data.get('tier', 'tier1')
    KYCService.approve_kyc(kyc_profile=profile, admin_user=request.user, tier=target_tier)
    return Response({'message': 'the KYC is approv.'})

  @action(detail=True, methods=['post'])
  def reject(self, request, pk=None):
    profile = self.get_object()
    reason_text = request.data.get('reason', 'unclear documents')
    KYCService.reject_kyc(kyc_profile=profile, reason=reason_text, admin_user=request.user)
    return Response({'messag': 'the KYC is reject'})

  @action(detail=False, methods=['post'])
  def verify_biometric(self, request):
    raw_input = request.data.get('biometric_raw')
    if not raw_input:
      return Response({'err': 'the data is need.'}, status=400)
    b_hash = BiometricService.hash_biometric_data(raw_input)
    is_valid = BiometricService.verify_with_nadra(b_hash)
    if not is_valid:
      return Response({'err': 'the verif has failed'}, status=400)      
    profile, created = KYCProfile.objects.get_or_create(user=request.user)
    profile.biometric_hash = b_hash
    profile.is_biometric_verified = True
    profile.save()
    return Response({'message': 'the biometric is verif'})