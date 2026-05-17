from rest_framework import viewsets, mixins
from wallets.models import Wallet, WalletRecord, WalletBookings
from wallets.serializers.detail import WalletSerializer
from wallets.permissions import InternalServiceGuard, WalletAccessPermission
from django.conf import settings
from wallets.selectors import WalletSelector
from rest_framework.decorators import action
from wallets.serializers.basic import InternalWalletCreateSerializer
from wallets.services import WalletService
from rest_framework.response import Response
from decimal import Decimal
from parent.sharding_utils import set_current_shard, clear_current_shard
from rest_framework_simplejwt.authentication import JWTTokenUserAuthentication
from parent.authentication import ServiceJWTAuthentication
from rest_framework.authentication import SessionAuthentication

class WalletViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
  queryset = Wallet.objects.all()
  serializer_class = WalletSerializer
  authentication_classes = [ServiceJWTAuthentication, SessionAuthentication]

  def get_permissions(self):
    if self.action == 'create_internal':
      return [InternalServiceGuard()]
    if self.action == 'upgrade_tier':
      return [InternalServiceGuard()]
    if self.action == 'check_balance':
      return [InternalServiceGuard()]
    if self.action == 'settle':
      return [InternalServiceGuard()]
    if self.action == 'reserve':
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

  @action(detail=False, methods=['post'], authentication_classes=[], url_path = 'create-internal')
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

  @action(detail=True, methods=['patch'], authentication_classes=[], url_path = 'upgrade_tier')
  def upgrade_tier(self, request, pk=None):
    wallet = self.get_object()
    new_tier = request.data.get('tier')
    valid_tiers = ['tier1', 'tier2', 'tier3']
    if new_tier in valid_tiers:
      WalletService.upgrade_tier(wallet_id=wallet.id, new_tier=new_tier)
      wallet.refresh_from_db()
      return Response(WalletSerializer(wallet).data, status=200)
    return Response({'err': 'wrong tier. it s/h be tier1, tier2, or tier3.'}, status=400)
  
  @action(detail=False, methods=['post'], permission_classes=[InternalServiceGuard], authentication_classes=[], url_path = 'check-balance')
  def check_balance(self, request):
    from parent.sharding_utils import get_shard_for_user, set_current_shard, clear_current_shard
    wallet_id = request.data.get('wallet_id')
    amount_str = request.data.get('amount')
    if not wallet_id or not amount_str:
      return Response({'err': 'wallet_id and amount are need.'}, status=400)
    try:
      amount = Decimal(str(amount_str))
    except (ValueError, TypeError):
      return Response({'err': 'Invalid amount format.'}, status=400)
    try:
      wallet = None
      for db in ['default', 'shard_1', 'shard_2']:
        try:
          wallet = Wallet.objects.using(db).get(id=wallet_id) 
          break
        except Wallet.DoesNotExist:
          continue
      if not wallet:
        return Response({'err': 'Wallet not found.'}, status=404)
      shard = get_shard_for_user(wallet.user_id)
      set_current_shard(shard)
      if wallet.status != 'active':
        return Response({'err': f'Wallet is {wallet.status}.'}, status=400)
      if wallet.available_balance >= amount:
        return Response({'status': 'sufficient', 'available': str(wallet.available_balance)}, status=200)
      return Response({'err': 'not enough balance.', 'available': str(wallet.available_balance), 'required': str(amount)}, status=400)
    finally:
      clear_current_shard()

  @action(detail=True, methods=['post'])
  def freeze(self, request, pk=None):
    auth = JWTTokenUserAuthentication()
    try:
      result = auth.authenticate(request)
      print('AUTH RESULT:', result)
    except Exception as e:
      print('AUTH ERROR:', e)
    wallet = self.get_object()
    if wallet.status == 'frozen':
      return Response({'message': 'the wallet is alr frozen.'}, status=400)
    wallet.status = 'frozen'
    wallet.save(update_fields=['status']) 
    return Response({'message': f'wallet {wallet.id} is now frozen.'}, status=200)
  
  @action(detail=True, methods=['post'])
  def unfreeze(self, request, pk=None):
    wallet = self.get_object()
    if wallet.status == 'active':
      return Response({'message': 'This wallet is already active.'}, status=400)
    wallet.status = 'active'
    wallet.save(update_fields=['status']) 
    return Response({'message': f'Wallet {wallet.id} is now active.'}, status=200)
  
  @action(detail=False, methods=['post'], authentication_classes=[])
  def reserve(self, request):
    wallet_id = request.data.get('wallet_id') 
    amount = request.data.get('amount')
    transaction_id = request.data.get('transaction_id')
    actual_shard = None
    if Wallet.objects.using('shard_1').filter(id=wallet_id).exists():
      actual_shard = 'shard_1'
    elif Wallet.objects.using('shard_2').filter(id=wallet_id).exists():
      actual_shard = 'shard_2'
    if not actual_shard:
      return Response({'err': 'Wallet not found'}, status=404)
    set_current_shard(actual_shard)

    try:
      wallet = Wallet.objects.get(id=wallet_id)
      booking = WalletService.reserve_funds(wallet_id=wallet.id, amount=amount, reason=f'TXN_{transaction_id}')
      return Response({'booking_id': str(booking.id)}, status=200)
    except ValueError as e:
      return Response({'err': str(e)}, status=400)
    finally:
      clear_current_shard()

  @action(detail=False, methods=['post'], authentication_classes=[])
  def settle(self, request):
    transaction_id = request.data.get('transaction_id')
    actual_shard = None
    try:
     booking_temp = WalletBookings.objects.using('shard_1').filter(reason=f'TXN_{transaction_id}', is_committed=False).first()
     if not booking_temp:
       booking_temp = WalletBookings.objects.using('shard_2').filter(reason=f'TXN_{transaction_id}', is_committed=False).first()
     if booking_temp:
       if WalletBookings.objects.using('shard_1').filter(reason=f'TXN_{transaction_id}', is_committed=False).exists():
        actual_shard = 'shard_1'
       else:
        actual_shard = 'shard_2'
       set_current_shard(actual_shard)
       booking = WalletBookings.objects.get(id=booking_temp.id)
       success = WalletService.commit_funds(booking.id)
       if success:
        return Response({'status': 'settled'}, status=200)
       return Response({'err': 'settlement failed'}, status=400)
     else:
       return Response({'err': 'no active booking is found for this transa'}, status=404)
    finally:
      clear_current_shard()