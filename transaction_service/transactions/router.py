from transactions.utils import get_transaction_shard

class TransactionShardRouter:
  def db_for_read(self, model, **hints):
    if model._meta.app_label == 'transactions':
      instance = hints.get('instance')
      if instance and hasattr(instance, 'created_at') and instance.created_at:
        return get_transaction_shard(instance.created_at)
      return get_transaction_shard()
    return 'default'

  def db_for_write(self, model, **hints):
    if model._meta.app_label == 'transactions':
      return get_transaction_shard()
    return 'default'

  def allow_relation(self, obj1, obj2, **hints):
    if obj1._meta.app_label == 'transactions':
      if obj2._meta.app_label == 'transactions':
        return True
    return None

  def allow_migrate(self, db, app_label, model_name=None, **hints):
    if app_label == 'transactions':
      if db.startswith('transaction_'):
        return True
      return False
    if db == 'default':
      return True      
    return False