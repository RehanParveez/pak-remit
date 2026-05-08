import threading

_thread_locals = threading.local()

def set_current_shard(shard_name):
  _thread_locals.current_shard = shard_name

def get_current_shard():
  return getattr(_thread_locals, 'current_shard', None)

def clear_current_shard():
  if hasattr(_thread_locals, 'current_shard'):
    del _thread_locals.current_shard

def get_shard_for_user(user_id):
  user_str = str(user_id)
  user_hash = hash(user_str)
  if user_hash % 2 == 0:
    return 'shard_1'
    
  return 'shard_2'