from rest_framework import viewsets, mixins
from wallets.models import Wallet, WalletRecord
from wallets.serializers.detail import WalletSerializer
from wallets.permissions import InternalServiceGuard, WalletAccessPermission
from django.conf import settings
from rest_framework.permissions import IsAdminUser
from wallets.selectors import WalletSelector
from rest_framework.decorators import action
from wallets.serializers.basic import InternalWalletCreateSerializer
from wallets.services import WalletService
from rest_framework.response import Response

class WalletViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
  queryset = Wallet.objects.all()
  serializer_class = WalletSerializer

  def get_permissions(self):
    if self.action == 'create_internal':
      return [InternalServiceGuard()]
    if self.action == 'upgrade_tier':
      return [InternalServiceGuard()]
    return [WalletAccessPermission()]

  def get_queryset(self):
    internal_token = self.request.headers.get('X-Internal-Token')
    if internal_token == settings.INTERNAL_SERVICE_SECRET:
      return self.queryset.all()
    auth_data = self.request.auth
    if not auth_data:
      return self.queryset.none()
    user_control = auth_data.get('control')
    is_staff = auth_data.get('is_staff', False)
    if user_control == 'admin' or is_staff:
      return self.queryset.all()
    user_id = auth_data.get('user_id')
    return WalletSelector.get_user_wallets(user_id)

  @action(detail=False, methods=['post'])
  def create_internal(self, request):
    serializer = InternalWalletCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user_id = serializer.validated_data['user_id']
    currency = serializer.validated_data.get('currency', 'pkr')
    wallet = WalletService.create_wallet(user_id=user_id, currency=currency)
    response_serializer = WalletSerializer(wallet)
    return Response(response_serializer.data, status=201)

  def retrieve(self, request, *args, **kwargs):
    wallet = self.get_object()
    serializer = self.get_serializer(wallet)
    data = serializer.data
    records = WalletRecord.objects.filter(wallet=wallet).order_by('-created_at')
    history = []
    for rec in records:
      history.append({'id': rec.id, 'amount': rec.amount, 'type': rec.type, 'description': rec.description, 'created_at': rec.created_at})  
    data['transaction_history'] = history
    return Response(data, status=200)

  @action(detail=True, methods=['patch'])
  def upgrade_tier(self, request, pk=None):
    wallet = self.get_object()
    new_tier = request.data.get('tier')
    valid_tiers = ['tier1', 'tier2', 'tier3']
    if new_tier in valid_tiers:
      WalletService.upgrade_tier(wallet_id=wallet.id, new_tier=new_tier)
      wallet.refresh_from_db()
      return Response(WalletSerializer(wallet).data, status=200)
    return Response({'err': 'wrong tier. it s/h be tier1, tier2, or tier3.'}, status=400)

  @action(detail=True, methods=['post'])
  def freeze(self, request, pk=None):
    wallet = self.get_object()
    if wallet.status == 'frozen':
      return Response({'message': 'the wallet is alr frozen.'}, status=400)
    wallet.status = 'frozen'
    wallet.save(update_fields=['status']) 
    return Response({'message': f'wallet {wallet.id} is now frozen.'}, status=200)