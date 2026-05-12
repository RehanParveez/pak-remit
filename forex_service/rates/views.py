from rest_framework import viewsets, permissions
from rates.services import ForexService
from parent.permissions import PakRemitPermission 
from rest_framework.decorators import action
from rates.models import CurrencyPair, ExchangeRate
from rest_framework.response import Response
from rates.serializers.basic import CurrencyConversionSerializer, RateUpdateSerializer
from django.utils import timezone

class ForexViewSet(viewsets.ViewSet):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.forex_service = ForexService()

  def get_permissions(self):
    if self.action == 'rates':
      return [permissions.AllowAny()]
    if self.action == 'update':
      return [PakRemitPermission()] 
    return [PakRemitPermission()]

  @action(detail=False, methods=['get'])
  def rates(self, request):
    active_pairs = CurrencyPair.objects.filter(is_active=True)
    results = {}
    for pair in active_pairs:
      rate = self.forex_service.get_current_rate(pair.base_currency, pair.quote_currency)
      key = f'{pair.base_currency.upper()}_{pair.quote_currency.upper()}'
      results[key] = float(rate) if rate else None
            
    return Response(results)

  @action(detail=False, methods=['get'])
  def convert(self, request):
    serializer = CurrencyConversionSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    converted_amount = self.forex_service.convert_amount(amount=data['amount'], from_currency=data['from_currency'], to_currency=data['to_currency'])
    rate = self.forex_service.get_current_rate(data['from_currency'], data['to_currency'])
    return Response({'converted_amount': float(converted_amount), 'rate': float(rate)})

  @action(detail=False, methods=['post'])
  def update_rate(self, request):
    if request.auth.get('control') != 'admin':
      return Response({'detail': 'the admin access is need.'}, status=403)     
    serializer = RateUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    ExchangeRate.objects.create(from_currency=serializer.validated_data['from_currency'].lower(), to_currency=serializer.validated_data['to_currency'].lower(),
      rate=serializer.validated_data['rate'], source=serializer.validated_data.get('source', 'manual'), effective_from=timezone.now())
    return Response({"message": 'the rate is updated'}, status=201)