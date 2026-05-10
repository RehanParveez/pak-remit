from rest_framework import viewsets
from parent.permissions import PakRemitPermission
from limits.serializers.basic import DailySpendingSerializer, MonthlySpendingSerializer, FraudFlagSerializer1
from limits.models import DailySpending, MonthlySpending, FraudFlag
from rest_framework.decorators import action
from limits.serializers.detail import FraudFlagSerializer, FraudResolutionSerializer
from rest_framework.response import Response

class SpendingViewSet(viewsets.ReadOnlyModelViewSet):
  permission_class = [PakRemitPermission]
  serializer_class = DailySpendingSerializer

  def get_queryset(self):
    user_auth = self.request.auth or {}
    user_id = user_auth.get('user_id')
    if user_auth.get('control') == 'admin':
      return DailySpending.objects.all() 
    return DailySpending.objects.filter(wallet__user_id=user_id)

  @action(detail=False, methods=['get'])
  def monthly_summary(self, request):
    user_auth = request.auth or {}
    user_id = user_auth.get('user_id')
    if user_auth.get('control') == 'admin':
      queryset = MonthlySpending.objects.all()
    else:
      queryset = MonthlySpending.objects.filter(wallet__user_id=user_id)
    serializer = MonthlySpendingSerializer(queryset, many=True)
    return Response(serializer.data)

class FraudFlagViewSet(viewsets.ModelViewSet):
  permission_classes = [PakRemitPermission]
  
  def get_queryset(self):
    user_auth = self.request.auth or {}
    user_control = user_auth.get('control')
    if user_control == 'admin' or user_auth.get('is_staff'):
      return FraudFlag.objects.all().select_related('wallet')
    token_user_id = user_auth.get('user_id')
    return FraudFlag.objects.filter(wallet__user_id=token_user_id).select_related('wallet')

  def get_serializer_class(self):
    if self.action == 'list':
      return FraudFlagSerializer1
    if self.action == 'resolve':
      return FraudResolutionSerializer
    return FraudFlagSerializer

  @action(detail=True, methods=['post'])
  def resolve(self, request, pk=None):
    user_auth = request.auth or {}
    user_control = user_auth.get('control')
    if user_control != 'admin' and not user_auth.get('is_staff'):
      return Response({'err': 'only the admins can resolve flags.'}, status=403)

    flag = self.get_object()
    if flag.is_resolved:
      return Response({'err': 'this flag is already resol'}, status=400)    
    serializer = FraudResolutionSerializer(flag, data=request.data, context={'request': request}, partial=True)
    if serializer.is_valid():
      serializer.save()
      return Response({'status': 'flag resolved'})
    return Response(serializer.errors, status=400)