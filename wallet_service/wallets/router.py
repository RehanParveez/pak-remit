from parent.sharding_utils import get_current_shard

class WalletShardRouter:
  SHARDED_APPS = ['wallets', 'limits']
  
  def db_for_read(self, model, **hints):
    if model._meta.app_label in self.SHARDED_APPS:
      shard = get_current_shard()
      if shard:
        return shard
    return 'default'

  def db_for_write(self, model, **hints):
    if model._meta.app_label in self.SHARDED_APPS:
      shard = get_current_shard()
      if shard:
        return shard
    return 'default'

  def allow_relation(self, obj1, obj2, **hints):
    if obj1._meta.app_label in self.SHARDED_APPS and \
      obj2._meta.app_label in self.SHARDED_APPS:
        return True 
    return None

  def allow_migrate(self, db, app_label, model_name=None, **hints):
    if app_label in self.SHARDED_APPS:
      return True     
    return None