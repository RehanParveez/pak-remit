from rest_framework import viewsets
from statements.models import BankStatement, SettlementDifference
from statements.serializers.detail import BankStatementSerializer, SettlementDifferenceSerializer
from parent.permissions import PakRemitPermission
from statements.serializers.basic import StatementUploadSerializer, DifferenceResolveSerializer, StatementListSerializer
from rest_framework.decorators import action
from statements.services import StatementParserService, SettlementService
from statements.tasks import process_uploaded_statement
from rest_framework.response import Response

class StatementViewSet(viewsets.ModelViewSet):
  queryset = BankStatement.objects.all()
  serializer_class = BankStatementSerializer
    
  def get_permissions(self):
    if self.action in ['upload', 'settle']:
     return [PakRemitPermission()]
    return [PakRemitPermission()]
    
  def get_serializer_class(self):
    if self.action == 'upload':
      return StatementUploadSerializer
    if self.action == 'list':
      return StatementListSerializer
    return BankStatementSerializer
    
  @action(detail=False, methods=['post'])
  def upload(self, request):
    serializer = StatementUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    statement = serializer.save()
        
    file = request.FILES.get('file')
    if file.name.endswith('.csv'):
      StatementParserService.parse_csv(file, statement)
    process_uploaded_statement.delay(str(statement.id))
    return Response({'message': 'the statement is uploaded', 'statement_id': str(statement.id)}, status=201)
    
  @action(detail=True, methods=['post'])
  def settle(self, request, pk=None):
    statement = self.get_object()
    result = SettlementService.settlement_statement(str(statement.id))
    return Response({'message': 'settlement completed', 'matched_count': result['matched_count'], 'difference_count': result['difference_count']}, status=200)

class DifferenceViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = SettlementDifference.objects.all()
  serializer_class = SettlementDifferenceSerializer
  permission_classes = [PakRemitPermission]
    
  def get_queryset(self):
    queryset = SettlementDifference.objects.all()
        
    is_resolved = self.request.query_params.get('status')
    if is_resolved == 'unresolved':
      queryset = queryset.filter(is_resolved=False)
    return queryset.order_by('-created_at')
    
  @action(detail=True, methods=['post'])
  def resolve(self, request, pk=None):
    difference = self.get_object()
    serializer = DifferenceResolveSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    resolved = SettlementService.resolve_difference(str(difference.id), serializer.validated_data['resolution'])
    return Response({'message': ' resolved', 'difference_id': str(resolved.id) }, status=200)