import logging
from enum import Enum
from django.core.cache import caches

logger = logging.getLogger(__name__)

class CircuitState(Enum):
  CLOSED = 'closed'
  OPEN = 'open'
  HALF_OPEN = 'half_open'

CIRCUIT_CONFIG = {
  'failure_limit': 5,
  'recovery_timeout': 60,
  'success_limit': 2,
}

def _cache():
  return caches['circuit_breaker']

def _key(name, suffix):
  return f'cb:{name}:{suffix}'

def get_state(name):
  state = _cache().get(_key(name, 'state'))
  if state is None:
    return CircuitState.CLOSED
  return CircuitState(state)

def _set_state(name, state, timeout=None):
  _cache().set(_key(name, 'state'), state.value, timeout=timeout)
  logger.warning('circuit breaker [%s] -> %s', name, state.value.upper())

def _get_failures(name):
  value = _cache().get(_key(name, 'failures'))
  if value is None:
    return 0
  return int(value)

def _increment_failures(name):
  key = _key(name, 'failures')
  try:
    _cache().incr(key)
  except ValueError:
    _cache().set(key, 1, timeout=300)

def _reset_failures(name):
  _cache().delete(_key(name, 'failures'))
  _cache().delete(_key(name, 'half_open_successes'))

def _get_half_open_successes(name):
  value = _cache().get(_key(name, 'half_open_successes'))
  if value is None:
    return 0
  return int(value)

def _increment_half_open_successes(name):
  key = _key(name, 'half_open_successes')
  try:
    _cache().incr(key)
  except ValueError:
    _cache().set(key, 1, timeout=300)

def breaker_call(name, func, *args, **kwargs):
  cfg = CIRCUIT_CONFIG
  state = get_state(name)

  if state == CircuitState.OPEN:
    logger.error('circuit [%s] is open — request blocked', name)
    return None, f"{name} is unavailable. retry after {cfg['recovery_timeout']}"
  if state == CircuitState.HALF_OPEN:
    logger.info('circuit [%s] is half-open — probing', name)
  try:
    response = func(*args, **kwargs)
    if hasattr(response, 'status_code'):
      if response.status_code >= 500:
        raise Exception(f'http {response.status_code} from downstream')
    if state == CircuitState.HALF_OPEN:
      _increment_half_open_successes(name)
      successes = _get_half_open_successes(name)
      if successes >= cfg['success_limit']:
        _set_state(name, CircuitState.CLOSED)
        _reset_failures(name)
        logger.info('circuit [%s] closed after recovery', name)
    else:
      _reset_failures(name)
    return response, None

  except Exception as exc:
     _increment_failures(name)
     failures = _get_failures(name)
     logger.error('circuit [%s] failure %d/%d: %s', name, failures, cfg['failure_limit'], exc)
     if state == CircuitState.HALF_OPEN:
      _set_state(name, CircuitState.OPEN, timeout=cfg['recovery_timeout'])
      _reset_failures(name)
     else:
      if failures >= cfg['failure_limit']:
        _set_state(name, CircuitState.OPEN, timeout=cfg['recovery_timeout'])
        _reset_failures(name)
     return None, str(exc)

WALLET_BREAKER = 'wallet_breaker'
IDENTITY_BREAKER = 'identity_breaker'
TRANSACTION_BREAKER = 'transaction_breaker'
LEDGER_BREAKER = 'ledger_breaker'
FOREX_BREAKER = 'forex_breaker'
NOTIFICATION_BREAKER = 'notification_breaker'