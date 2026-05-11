from django.db import transaction
from events.models import EventProjection, RecordEvent

class ProjectionBuilder:
  @classmethod
  def update_projection(cls, event):
    projection, created = EventProjection.objects.using(None).get_or_create(aggregate_id=event.aggregate_id,
      defaults={'aggregate_type': event.aggregate_type, 'last_event_id': event.id, 'version': 0,
        'trace_id': event.trace_id})
    updated_state = projection.current_state.copy()
    updated_state.update(event.payload)
    projection.current_state = updated_state
    projection.last_event_id = event.id
    projection.version += 1
    projection.trace_id = event.trace_id
        
    projection.save(using=None)
    return projection

  @classmethod
  def rebuild_projection(cls, aggregate_id):
    events = EventStore.get_events_for_aggregate(aggregate_id)
    if not events:
      return None
    rebuilt_state = {}
    last_event = None 
    for event in events:
      rebuilt_state.update(event.payload)
      last_event = event

    projection, _ = EventProjection.objects.using(None).update_or_create(aggregate_id=aggregate_id,
      defaults={'aggregate_type': last_event.aggregate_type, 'current_state': rebuilt_state, 'last_event_id': last_event.id, 
        'version': events.count(), 'trace_id': last_event.trace_id})
    return projection

class EventStore:
  @classmethod
  def append_event(cls, event_type, aggregate_id, aggregate_type, payload, user_id=None, trace_id=None):
    with transaction.atomic(using=None):
      event = RecordEvent.objects.using(None).create(event_type=event_type, aggregate_id=aggregate_id,
        aggregate_type=aggregate_type, payload=payload, user_id=user_id, trace_id=trace_id)       
      ProjectionBuilder.update_projection(event)
      return event

  @classmethod
  def get_events_for_aggregate(cls, aggregate_id):
    return RecordEvent.objects.using(None).filter(aggregate_id=aggregate_id).order_by('created_at')

  @classmethod
  def replay_events(cls, aggregate_id):
    events = cls.get_events_for_aggregate(aggregate_id)
    state = {}
    for event in events:
      state.update(event.payload)
    return state

  @classmethod
  def get_event_stream(cls, start_id=None):
    queryset = RecordEvent.objects.using(None).all()
    if start_id:
      queryset = queryset.filter(id__gt=start_id)
    return queryset.order_by('created_at')