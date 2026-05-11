from rest_framework import viewsets
from refunds.models import Refund
from parent.permissions import PakRemitPermission
from refunds.serializers.basic import RefundBasicSerializer
from refunds.serializers.detail import RefundRequestSerializer, RefundDetailSerializer
from transactions.services import shard_context
from rest_framework.decorators import action
from refunds.services import RefundService
from rest_framework.response import Response

class RefundViewSet(viewsets.ModelViewSet):
  queryset = Refund.objects.all()
  permission_classes = [PakRemitPermission]
    
  def get_serializer_class(self):
    if self.action == 'list':
      return RefundBasicSerializer    
    if self.action == 'request_refund':
      return RefundRequestSerializer  
    return RefundDetailSerializer

  def get_queryset(self):
    user_auth = self.request.auth
    user_id = user_auth.get('user_id')
    user_control = user_auth.get('control')

    with shard_context():
      if user_control == 'admin':
        return Refund.objects.all().order_by('-created_at')    
      return Refund.objects.filter(requested_by=user_id).order_by('-created_at')

  @action(detail=False, methods=['post'], url_path='request')
  def request_refund(self, request):
    serializer = RefundRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True) 
    user_id = request.auth.get('user_id')
        
    refund_obj = RefundService.create_refund_request(transaction_id=serializer.validated_data['transaction_id'],
      amount=serializer.validated_data['amount'], reason=serializer.validated_data['reason'], user_id=user_id)
    response_data = RefundDetailSerializer(refund_obj).data
    return Response(response_data, status=201)

  @action(detail=True, methods=['post'], url_path='approve')
  def approve(self, request, pk=None):
    user_auth = request.auth
    user_control = user_auth.get('control')
    is_staff = user_auth.get('is_staff')

    if user_control != 'admin':
      if not is_staff:
        return Response({'err': 'the admin access is need.'}, status=403)
    admin_id = user_auth.get('user_id')
    refund_obj = RefundService.approve_refund(refund_id=pk, admin_id=admin_id) 
    response_data = RefundDetailSerializer(refund_obj).data
    return Response(response_data)

  @action(detail=True, methods=['post'])
  def process(self, request, pk=None):
    user_auth = request.auth
    user_control = user_auth.get('control')
    is_staff = user_auth.get('is_staff')
    if user_control != 'admin':
      if not is_staff:
        return Response({'err': 'the access to system is need.'}, status=403)
    refund_obj = RefundService.process_refund(refund_id=pk)
    serializer = RefundDetailSerializer(refund_obj)
    return Response(serializer.data)