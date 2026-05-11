from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets
from transactions.models import Transaction
from transactions.serializers.detail import TransactionSerializer
from rest_framework.decorators import action
from parent.permissions import PakRemitPermission
from django.utils.dateparse import parse_date
from django.db.models import Q
from transactions.permissions import EnoughBalancePerm, RefundPermission
from rest_framework.response import Response
from transactions.services import TransactionService, shard_context, IdempotencyService

class TransactionPagination(PageNumberPagination):
    page_size = 40

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = Transaction.objects.all()
  serializer_class = TransactionSerializer
  pagination_class = TransactionPagination
  permission_classes = [PakRemitPermission]

  def get_queryset(self):
    user_auth = self.request.auth
    user_id = user_auth.get('user_id')
    txn_status = self.request.query_params.get('status')
    start_date = self.request.query_params.get('start_date')
    query_timestamp = None
    if start_date:
      query_timestamp = parse_date(start_date)
        
    with shard_context(timestamp=query_timestamp):
      queryset = Transaction.objects.filter(Q(from_wallet_id=user_id) | Q(to_wallet_id=user_id))
      if txn_status:
        queryset = queryset.filter(status=txn_status)
      if start_date:
        queryset = queryset.filter(created_at__gte=start_date)
      return queryset.order_by('-created_at')

  @action(detail=False, methods=['post'], url_path='p2p', permission_classes=[PakRemitPermission, EnoughBalancePerm])
  def p2p_transfer(self, request):
    idempotency_key = request.META.get('HTTP_IDEMPOTENCY_KEY')
    if not idempotency_key:
      return Response({'err': 'Idempotency-Key header is need'}, status=400)
    cached_response = IdempotencyService.check_duplicate(idempotency_key)
    if cached_response:
      return Response(cached_response, status=200)
    txn = TransactionService.initiate_transaction(from_wallet_id=request.data.get('from_wallet_id'), to_wallet_id=request.data.get('to_wallet_id'), amount=request.data.get('amount'), 
      currency=request.data.get('currency', 'pkr'), idempotency_key=idempotency_key, txn_type = 'p2p')
    response_data = {'transaction_id': str(txn.id), 'status': txn.status, 'estimated_completion': 'Immediate'}
    IdempotencyService.cache_response(idempotency_key, response_data)
    return Response(response_data, status=201)

  @action(detail=False, methods=['post'], permission_classes=[PakRemitPermission, EnoughBalancePerm])
  def merchant_payment(self, request):
    idempotency_key = request.META.get('HTTP_IDEMPOTENCY_KEY')
    if not idempotency_key:
      return Response({'err': 'Idempotency-Key header is need.'}, status=400) 
    metadata = {'merchant_name': request.data.get('merchant_name'), 'invoice_id': request.data.get('invoice_id')}
    txn = TransactionService.initiate_transaction(from_wallet_id=request.data.get('wallet_id'), to_wallet_id=request.data.get('merchant_id'),
      amount=request.data.get('amount'), currency=request.data.get('currency', 'pkr'), idempotency_key=idempotency_key, txn_type = 'merchant', metadata=metadata)  
    serializer = self.get_serializer(txn)
    return Response(serializer.data, status=201)

  @action(detail=True, methods=['post'], permission_classes=[PakRemitPermission, RefundPermission])
  def refund(self, request, pk=None):
    reason = request.data.get('reason', 'User requested refund')
    refund_txn = TransactionService.refund_transaction(original_transaction_id=pk, reason=reason)
    return Response({'message': 'Refund initiated', 'refund_id': refund_txn.id}, status=201)