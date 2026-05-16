import json
from parent.sharding_utils import set_current_shard, clear_current_shard, get_shard_for_user
INTERNAL_PATHS = ['/create-internal/', '/check-balance/', '/reserve/', '/settle/', '/upgrade-tier/']

class ShardRoutingMiddleware:
  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    user_id = None
    is_internal = any(path in request.path for path in INTERNAL_PATHS)
    if is_internal and request.method == 'POST':
      if request.body:
        try:
          body_data = json.loads(request.body)
          user_id = body_data.get('user_id')
        except json.JSONDecodeError:
          pass
    elif request.user.is_authenticated:
        user_id = request.user.id
        
    if user_id:
      shard_name = get_shard_for_user(user_id)
      set_current_shard(shard_name)
    try:
      response = self.get_response(request)
    finally: 
      clear_current_shard()
        
    return response