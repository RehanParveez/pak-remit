import uuid

class RecordRouter:
  def _get_shard(self, aggregate_id):
    if not aggregate_id:
      return 'default'
    try:
      shard_index = (uuid.UUID(str(aggregate_id)).int % 2) + 1
      return f'record_shard_{shard_index}'
    except (ValueError, TypeError):
      return 'default'

  def db_for_read(self, model, **hints):
    if model._meta.app_label == 'events':
      aggregate_id = hints.get('aggregate_id')
      instance = hints.get('instance')
      if not aggregate_id and instance:
        aggregate_id = getattr(instance, 'aggregate_id', None)
            
      return self._get_shard(aggregate_id)
    return 'default'

  def db_for_write(self, model, **hints):
    if model._meta.app_label == 'events':
      aggregate_id = hints.get('aggregate_id')
      instance = hints.get('instance')
      if not aggregate_id and instance:
        aggregate_id = getattr(instance, 'aggregate_id', None)
                
      return self._get_shard(aggregate_id)
    return 'default'

  def allow_relation(self, obj1, obj2, **hints):
    if obj1._meta.app_label == 'events' or obj2._meta.app_label == 'events':
      return True
    return None

  def allow_migrate(self, db, app_label, model_name=None, **hints):
    if app_label == 'events':
      return db in ['record_shard_1', 'record_shard_2', 'default']
    if db == 'default':
      return True
    return False