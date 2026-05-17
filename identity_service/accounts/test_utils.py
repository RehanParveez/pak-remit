from unittest.mock import MagicMock
from django.test import TestCase, override_settings
from parent.circuit_utils import _reset_failures, CircuitState, breaker_call, get_state,  CIRCUIT_CONFIG, WALLET_BREAKER, _set_state, _get_failures, _get_half_open_successes
from django.core.cache import caches
import uuid
import threading
from parent.sharding_utils import set_current_shard, clear_current_shard, get_current_shard, get_shard_for_user
import time

TEST_CACHE_SETTINGS = {
  'default': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
  },
  'circuit_breaker': {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
  },
}

BREAKER = 'test_breaker'

def mock_response(status_code):
  r = MagicMock()
  r.status_code = status_code
  return r

def successful_func(*args, **kwargs):
  return mock_response(200)

def failing_func(*args, **kwargs):
  raise Exception('downstream error')

def server_error_func(*args, **kwargs):
  return mock_response(500)

@override_settings(CACHES=TEST_CACHE_SETTINGS)
class CircuitBreaker_ClosedStateTests(TestCase):

  def setUp(self):
    _reset_failures(BREAKER)
    caches['circuit_breaker'].clear()

  def test_initial_state_is_closed(self):
    self.assertEqual(get_state(BREAKER), CircuitState.CLOSED)

  def test_successful_call_returns_response(self):
    response, error = breaker_call(BREAKER, successful_func)
    self.assertIsNotNone(response)
    self.assertIsNone(error)

  def test_successful_call_returns_200(self):
    response, error = breaker_call(BREAKER, successful_func)
    self.assertEqual(response.status_code, 200)

  def test_successful_call_keeps_state_closed(self):
    breaker_call(BREAKER, successful_func)
    self.assertEqual(get_state(BREAKER), CircuitState.CLOSED)

  def test_successful_call_resets_failures(self):
    breaker_call(BREAKER, failing_func)
    breaker_call(BREAKER, successful_func)
    self.assertEqual(_get_failures(BREAKER), 0)

  def test_single_failure_does_not_open_circuit(self):
    breaker_call(BREAKER, failing_func)
    self.assertEqual(get_state(BREAKER), CircuitState.CLOSED)

  def test_failure_returns_none_response(self):
    response, error = breaker_call(BREAKER, failing_func)
    self.assertIsNone(response)

  def test_failure_returns_error_string(self):
    response, error = breaker_call(BREAKER, failing_func)
    self.assertIsNotNone(error)
    self.assertIsInstance(error, str)

  def test_500_response_counts_as_failure(self):
    breaker_call(BREAKER, server_error_func)
    self.assertEqual(_get_failures(BREAKER), 1)

  def test_passes_args_to_func(self):
    called_with = {}
    def capture_func(*args, **kwargs):
      called_with['args'] = args
      called_with['kwargs'] = kwargs
      return mock_response(200)
    breaker_call(BREAKER, capture_func, 'arg1', key = 'val')
    self.assertEqual(called_with['args'], ('arg1',))
    self.assertEqual(called_with['kwargs'], {'key': 'val'})

@override_settings(CACHES=TEST_CACHE_SETTINGS)
class CircuitBreaker_FailureThresholdTests(TestCase):

  def setUp(self):
    _reset_failures(BREAKER)
    caches['circuit_breaker'].clear()

  def _trigger_failures(self, count):
    for _ in range(count):
      breaker_call(BREAKER, failing_func)

  def test_circuit_opens_after_failure_limit(self):
    self._trigger_failures(CIRCUIT_CONFIG['failure_limit'])
    self.assertEqual(get_state(BREAKER), CircuitState.OPEN)

  def test_circuit_stays_closed_before_failure_limit(self):
    self._trigger_failures(CIRCUIT_CONFIG['failure_limit'] - 1)
    self.assertEqual(get_state(BREAKER), CircuitState.CLOSED)

  def test_logs_error_on_failure(self):
    with self.assertLogs('parent.circuit_utils', level = 'ERROR'):
      breaker_call(BREAKER, failing_func)

  def test_failure_count_increments(self):
    self._trigger_failures(3)
    self.assertEqual(_get_failures(BREAKER), 3)

@override_settings(CACHES=TEST_CACHE_SETTINGS)
class CircuitBreaker_OpenStateTests(TestCase):

  def setUp(self):
    caches['circuit_breaker'].clear()
    _set_state(BREAKER, CircuitState.OPEN, timeout=60)

  def test_open_circuit_blocks_request(self):
    response, error = breaker_call(BREAKER, successful_func)
    self.assertIsNone(response)
    self.assertIsNotNone(error)

  def test_open_circuit_returns_unavailable_message(self):
    response, error = breaker_call(BREAKER, successful_func)
    self.assertIn('unavailable', error)

  def test_open_circuit_does_not_call_func(self):
    called = []
    def tracking_func(*args, **kwargs):
      called.append(True)
      return mock_response(200)
    breaker_call(BREAKER, tracking_func)
    self.assertEqual(len(called), 0)

  def test_open_circuit_logs_error(self):
    with self.assertLogs('parent.circuit_utils', level = 'ERROR'):
      breaker_call(BREAKER, successful_func)

  def test_state_remains_open(self):
    breaker_call(BREAKER, successful_func)
    self.assertEqual(get_state(BREAKER), CircuitState.OPEN)

@override_settings(CACHES=TEST_CACHE_SETTINGS)
class CircuitBreaker_HalfOpenStateTests(TestCase):

  def setUp(self):
    caches['circuit_breaker'].clear()
    _set_state(BREAKER, CircuitState.HALF_OPEN)

  def test_half_open_allows_probe_request(self):
    response, error = breaker_call(BREAKER, successful_func)
    self.assertIsNotNone(response)
    self.assertIsNone(error)

  def test_half_open_success_increments_counter(self):
    breaker_call(BREAKER, successful_func) 
    self.assertEqual(_get_half_open_successes(BREAKER), 1)

  def test_half_open_closes_after_success_limit(self):
    for _ in range(CIRCUIT_CONFIG['success_limit']):
      breaker_call(BREAKER, successful_func)
    self.assertEqual(get_state(BREAKER), CircuitState.CLOSED)

  def test_half_open_failure_reopens_circuit(self):
    breaker_call(BREAKER, failing_func)
    self.assertEqual(get_state(BREAKER), CircuitState.OPEN)

  def test_half_open_failure_resets_failures(self):
    breaker_call(BREAKER, failing_func)
    self.assertEqual(_get_failures(BREAKER), 0)

@override_settings(CACHES=TEST_CACHE_SETTINGS)
class CircuitBreaker_MultipleBreakersTests(TestCase):

  def setUp(self):
    caches['circuit_breaker'].clear()

  def test_different_breakers_are_independent(self):
    breaker_a = 'breaker_a'
    breaker_b = 'breaker_b'
    for _ in range(CIRCUIT_CONFIG['failure_limit']):
      breaker_call(breaker_a, failing_func)
    self.assertEqual(get_state(breaker_a), CircuitState.OPEN)
    self.assertEqual(get_state(breaker_b), CircuitState.CLOSED)

  def test_wallet_breaker_constant_works(self):
    response, error = breaker_call(WALLET_BREAKER, successful_func)
    self.assertIsNone(error)

class ShardingUtils_BasicTests(TestCase):

  def tearDown(self):
    clear_current_shard()

  def test_get_current_shard_returns_none_by_default(self):
    self.assertIsNone(get_current_shard())

  def test_set_and_get_shard(self):
    set_current_shard('shard_1')
    self.assertEqual(get_current_shard(), 'shard_1')

  def test_set_shard_2(self):
    set_current_shard('shard_2')
    self.assertEqual(get_current_shard(), 'shard_2')

  def test_clear_shard(self):
    set_current_shard('shard_1')
    clear_current_shard()
    self.assertIsNone(get_current_shard())

  def test_clear_shard_when_not_set(self):
    try:
      clear_current_shard()
    except Exception as exc:
      self.fail(f'clear_current_shard crashed when shard not set: {exc}')

  def test_overwrite_shard(self):
    set_current_shard('shard_1')
    set_current_shard('shard_2')
    self.assertEqual(get_current_shard(), 'shard_2')

  def test_get_shard_for_user_returns_valid_shard(self):
    shard = get_shard_for_user('some-user-uuid')
    self.assertIn(shard, ['shard_1', 'shard_2'])

  def test_get_shard_for_user_is_deterministic(self):
    uid = 'consistent-user-uuid-123'
    shard_a = get_shard_for_user(uid)
    shard_b = get_shard_for_user(uid)
    self.assertEqual(shard_a, shard_b)

  def test_get_shard_accepts_integer_user_id(self):
    shard = get_shard_for_user(12345)
    self.assertIn(shard, ['shard_1', 'shard_2'])

  def test_get_shard_accepts_uuid_string(self):
    shard = get_shard_for_user(str(uuid.uuid4()))
    self.assertIn(shard, ['shard_1', 'shard_2'])

class ShardingUtils_ThreadSafetyTests(TestCase):

  def tearDown(self):
    clear_current_shard()

  def test_thread_locals_are_isolated(self):
    results = {}
    barrier = threading.Barrier(2)
    def thread_task(name, shard):
      set_current_shard(shard)
      barrier.wait()
      results[name] = get_current_shard()

    t1 = threading.Thread(target=thread_task, args=('t1', 'shard_1'))
    t2 = threading.Thread(target=thread_task, args=('t2', 'shard_2'))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    self.assertEqual(results['t1'], 'shard_1')
    self.assertEqual(results['t2'], 'shard_2')

  def test_shard_not_visible_across_threads(self):
    seen = []
    def thread_a():
      set_current_shard('shard_1')
    def thread_b():
      time.sleep(0.05)
      seen.append(get_current_shard())

    ta = threading.Thread(target=thread_a)
    tb = threading.Thread(target=thread_b)
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    self.assertIsNone(seen[0])

  def test_clear_in_one_thread_does_not_affect_other(self):
    results = {}
    barrier = threading.Barrier(2)
    def thread_a():
      set_current_shard('shard_1')
      barrier.wait()
      clear_current_shard()
    def thread_b():
      set_current_shard('shard_2')
      barrier.wait()
      time.sleep(0.05)
      results['b'] = get_current_shard()

    ta = threading.Thread(target=thread_a)
    tb = threading.Thread(target=thread_b)
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    self.assertEqual(results['b'], 'shard_2')