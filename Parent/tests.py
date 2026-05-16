from django.http import HttpResponse
from parent.middleware import PakRemitTracingMiddleware, get_current_trace_id
from django.test import SimpleTestCase, RequestFactory 
import json
import threading
import time

def _tracing_middleware(view_fn=None):
  if view_fn is None: view_fn = lambda r: HttpResponse('ok')
  return PakRemitTracingMiddleware(get_response=view_fn)

class TracingMiddleware_TraceIdGenerationTests(SimpleTestCase):
  def setUp(self):
    self.factory = RequestFactory()
    self.mw = _tracing_middleware()

  def test_generates_trace_id_when_header_absent(self):
    request = self.factory.get('/wallets/wallet/')
    self.mw(request)
    self.assertTrue(hasattr(request, 'trace_id'), 'the trace_id attri was not set')
    self.assertTrue(request.trace_id.startswith('pk_remit_'), f'Expected prefix pk_remit_, got: {request.trace_id}')
    self.assertEqual(len(request.trace_id), 21, f'Expected length 21, got {len(request.trace_id)}')

  def test_hex_suffix_is_valid_hexadecimal(self):
    request = self.factory.get('/wallets/wallet/')
    self.mw(request)
    suffix = request.trace_id[len('pk_remit_'):]
    try: int(suffix, 16)
    except ValueError: self.fail(f'Suffix {suffix!r} is not valid hex')

  def test_preserves_existing_trace_id_from_header(self):
    existing = 'upstream_service_trace_che023'
    request = self.factory.get('/wallets/wallet/', HTTP_X_TRACE_ID=existing)
    self.mw(request)
    self.assertEqual(request.trace_id, existing, 's/h not overwrite the existing trace id')

  def test_empty_string_trace_id_header_triggers_generation(self):
    request = self.factory.get('/wallets/wallet/', HTTP_X_TRACE_ID='')
    self.mw(request)
    self.assertTrue(request.trace_id.startswith('pk_remit_'), 'Empty header should trigger generation')

  def test_two_requests_get_different_trace_ids(self):
    req1, req2 = self.factory.get('/wallets/wallet/'), self.factory.get('/wallets/wallet/')
    self.mw(req1); self.mw(req2)
    self.assertNotEqual(req1.trace_id, req2.trace_id, 'Distinct requests got same trace_id')

class TracingMiddleware_ResponseHeaderTests(SimpleTestCase):
  def setUp(self): self.factory = RequestFactory()

  def test_response_contains_x_trace_id_header(self):
    mw = _tracing_middleware(lambda r: HttpResponse('ok'))
    request = self.factory.get('/wallets/wallet/')
    response = mw(request)
    self.assertIn('X-Trace-ID', response, 'response s/h echo back the X-Trace-ID header')
    self.assertEqual(response['X-Trace-ID'], request.trace_id)

  def test_response_preserves_caller_supplied_trace_id(self):
    caller_trace = 'caller_supplied_trace_xyz'
    mw = _tracing_middleware(lambda r: HttpResponse('ok'))
    request = self.factory.get('/wallets/wallet/', HTTP_X_TRACE_ID=caller_trace)
    response = mw(request)
    self.assertEqual(response['X-Trace-ID'], caller_trace)

class TracingMiddleware_LoggingTests(SimpleTestCase):
  def setUp(self):
    self.factory = RequestFactory()
    self.mw = _tracing_middleware()

  def test_logs_info_with_trace_id_method_and_path(self):
    request = self.factory.get('/wallets/wallet/')
    with self.assertLogs('parent.middleware', level='INFO') as cm:
      self.mw(request)
    combined = '\n'.join(cm.output)
    self.assertIn('trace:', combined)
    self.assertIn('GET', combined)
    self.assertIn('/wallets/wallet/', combined)
    self.assertIn(request.trace_id, combined)

  def test_process_exception_logs_error_with_trace_id(self):
    request = self.factory.get('/wallets/wallet/')
    request.trace_id = 'test_trace_debug_023'
    with self.assertLogs('parent.middleware', level='ERROR') as cm:
      self.mw.process_exception(request, ValueError('Something exploded'))
    combined = '\n'.join(cm.output)
    self.assertIn('test_trace_debug_023', combined)
    self.assertIn('Something exploded', combined)

  def test_process_exception_handles_missing_trace_id(self):
    request = self.factory.get('/wallets/wallet/')
    with self.assertLogs('parent.middleware', level='ERROR') as cm:
      self.mw.process_exception(request, RuntimeError('Edge case error'))
    self.assertIn('unknown', '\n'.join(cm.output))

  def test_logs_post_requests(self):
    request = self.factory.post('/transactions/transaction/p2p/', data=json.dumps({'amount': 100}), content_type='application/json')
    with self.assertLogs('parent.middleware', level='INFO') as cm:
      self.mw(request)
    combined = '\n'.join(cm.output)
    self.assertIn('POST', combined)
    self.assertIn('/transactions/transaction/p2p/', combined)

class TracingMiddleware_ThreadSafetyTests(SimpleTestCase):
  def setUp(self):
    self.factory = RequestFactory()
    self.mw = _tracing_middleware()

  def test_concurrent_requests_get_unique_trace_ids(self):
    collected = []
    lock = threading.Lock()

    def make_request():
      req = self.factory.get('/wallets/wallet/')
      self.mw(req)
      with lock: collected.append(req.trace_id)
    threads = [threading.Thread(target=make_request) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    self.assertEqual(len(collected), 10)
    self.assertEqual(len(collected), len(set(collected)), 'the duplicate trace_ids are detected across threads')

  def test_thread_local_trace_id_not_shared_between_threads(self):
    barrier = threading.Barrier(2)
    results = {}

    def thread_task(name, delay):
      req = self.factory.get('/wallets/wallet/')
      self.mw(req)
      barrier.wait()
      time.sleep(delay)
      results[name] = get_current_trace_id()
    t_a = threading.Thread(target=thread_task, args=('A', 0.01))
    t_b = threading.Thread(target=thread_task, args=('B', 0.02))
    t_a.start(); t_b.start()
    t_a.join(); t_b.join()
    self.assertNotEqual(results.get('A'), results.get('B'), 'thread locals leaked b/w threads')