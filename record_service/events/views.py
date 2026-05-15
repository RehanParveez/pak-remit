from rest_framework import viewsets, permissions
from events.permissions import InternalServiceGuard
from parent.permissions import PakRemitPermission
from rest_framework.decorators import action
from events.services import EventStore, ProjectionBuilder
from events.serializers.detail import RecordEventSerializer
from rest_framework.response import Response
from events.serializers.basic import EventAppendSerializer, EventReplaySerializer

class EventViewSet(viewsets.ViewSet):
  def get_permissions(self):
    print('ACTION:', self.action)
    if self.action == 'append':
      return [InternalServiceGuard()]
    if self.action in ['wallet_events', 'transaction_events', 'replay']:
      return [PakRemitPermission()]
    return [permissions.IsAuthenticated()]

  @action(detail=False, methods=['post'], authentication_classes=[])
  def append(self, request):
    serializer = EventAppendSerializer(data=request.data)
    if serializer.is_valid():
      event = EventStore.append_event(event_type=serializer.validated_data['event_type'], aggregate_id=serializer.validated_data['aggregate_id'],
        aggregate_type=serializer.validated_data['aggregate_type'], payload=serializer.validated_data['payload'], user_id=serializer.validated_data.get('user_id'),
        trace_id=serializer.validated_data.get('trace_id'))
      return Response({'event_id': str(event.id), 'timestamp': event.created_at}, status=201)
    return Response(serializer.errors, status=400)

  @action(detail=False, methods=['get'], url_path='wallet/(?P<wallet_id>[^/.]+)')
  def wallet_events(self, request, wallet_id=None):
    events = EventStore.get_events_for_aggregate(wallet_id)
    user_control = request.auth.get('control')
    if user_control != 'admin':
      requesting_user_id = str(request.auth.get('user_id'))
      events = events.filter(user_id=requesting_user_id)
            
    serializer = RecordEventSerializer(events, many=True)
    return Response(serializer.data)

  @action(detail=False, methods=['get'], url_path='transaction/(?P<transaction_id>[^/.]+)')
  def transaction_events(self, request, transaction_id=None):
    events = EventStore.get_events_for_aggregate(transaction_id)
    user_control = request.auth.get('control')
    if user_control != 'admin':
      requesting_user_id = str(request.auth.get('user_id'))
      events = events.filter(user_id=requesting_user_id)
            
    serializer = RecordEventSerializer(events, many=True)
    return Response(serializer.data)

  @action(detail=False, methods=['post'])
  def replay(self, request):
    serializer = EventReplaySerializer(data=request.data)
    if serializer.is_valid():
      projection = ProjectionBuilder.rebuild_projection(serializer.validated_data['aggregate_id'])
      if projection:
        return Response({'status': 'projection rebuilt', 'aggregate_id': str(projection.aggregate_id), 'version': projection.version})
      return Response({'err': 'no events are pres for this id'}, status=404)
    return Response(serializer.errors, status=400)