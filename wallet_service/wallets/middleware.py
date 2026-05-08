import json
from parent.sharding_utils import set_current_shard, clear_current_shard, get_shard_for_user

class ShardRoutingMiddleware:
  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    user_id = None
    if request.user.is_authenticated:
      user_id = request.user.id
    else:
      if '/create-internal/' in request.path:
        if request.method == "POST":
          if request.body:
            body_data = json.loads(request.body)        
            if 'user_id' in body_data:
              user_id = body_data.get('user_id')
    if user_id:
      shard_name = get_shard_for_user(user_id)
      set_current_shard(shard_name)
    response = self.get_response(request)
    clear_current_shard()
        
    return response