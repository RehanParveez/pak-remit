import logging
import threading
import uuid

logger = logging.getLogger(__name__)
_thread_locals = threading.local()

def get_current_trace_id():
  return getattr(_thread_locals, 'trace_id', None)

class PakRemitTracingMiddleware:
  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    trace_id = request.headers.get('X-Trace-ID')
    if not trace_id:
      trace_id = f'pk_remit_{uuid.uuid4().hex[:12]}' 
        
    _thread_locals.trace_id = trace_id
    request.trace_id = trace_id
    logger.info(f'trace: {trace_id} {request.method} {request.path}')
    response = self.get_response(request)
    response['X-Trace-ID'] = trace_id
    return response

  def process_exception(self, request, exception):
    trace_id = getattr(request, 'trace_id', 'unknown')
    logger.error(f'trace id: {trace_id} | Error: {str(exception)}')