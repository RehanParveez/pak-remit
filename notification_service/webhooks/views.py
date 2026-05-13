from rest_framework import viewsets
from webhooks.models import WebhookEndpoint, WebhookDelivery
from webhooks.serializers.detail import WebhookEndpointSerializer, WebhookDeliverySerializer
from parent.permissions import PakRemitPermission
from webhooks.serializers.basic import WebhookRegisterSerializer, WebhookListSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class WebhookEndpointViewSet(viewsets.ModelViewSet):
  queryset = WebhookEndpoint.objects.all()
  serializer_class = WebhookEndpointSerializer
  permission_classes = [PakRemitPermission]
    
  def get_queryset(self):
    user_auth = self.request.auth
    user_control = user_auth.get('control')
    if user_control == 'admin':
      return WebhookEndpoint.objects.all()
    merchant_id = user_auth.get('user_id')
    return WebhookEndpoint.objects.filter(merchant_id=merchant_id)
    
  def get_serializer_class(self):
    if self.action == 'register':
      return WebhookRegisterSerializer
    if self.action == 'list':
      return WebhookListSerializer
    return WebhookEndpointSerializer
    
  @action(detail=False, methods=['post'])
  def register(self, request):
    serializer = WebhookRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    merchant_id = request.auth.get('user_id')
    endpoint = serializer.save(merchant_id=merchant_id)
    return Response({'endpoint_id': str(endpoint.id), 'secret': endpoint.secret, 'url': endpoint.url}, status=201)

class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = WebhookDelivery.objects.all()
  serializer_class = WebhookDeliverySerializer
  permission_classes = [PakRemitPermission]
    
  def get_queryset(self):
    user_auth = self.request.auth
    user_control = user_auth.get('control') 
    queryset = WebhookDelivery.objects.all() 
    if user_control != 'admin':
      merchant_id = user_auth.get('user_id')
      queryset = queryset.filter(endpoint__merchant_id=merchant_id) 
    delivery_status = self.request.query_params.get('status')
    if delivery_status:
      queryset = queryset.filter(status=delivery_status)
        
    return queryset.order_by('-created_at')