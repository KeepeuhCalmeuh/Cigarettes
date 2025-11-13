import pytest
from src.network.connection_handshake import HandshakeMixin
from datetime import datetime, timedelta

class DummyHandshake(HandshakeMixin):
    def __init__(self):
        self._last_renewal_time = datetime.now() - timedelta(minutes=61)
        self._message_count = 10001
        self.RENEW_AFTER_MESSAGES = 10000
        self.RENEW_AFTER_MINUTES = 60
        self.connected = True
        self._stop_flag = type('Flag', (), {'is_set': lambda self: False})()


def test_is_onion_address():
    obj = DummyHandshake()
    assert obj._is_onion_address('abc.onion')
    assert not obj._is_onion_address('1.2.3.4')

def test_should_renew_connection():
    obj = DummyHandshake()
    assert obj._should_renew_connection() 