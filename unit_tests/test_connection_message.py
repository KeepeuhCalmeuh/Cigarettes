import pytest
from unittest.mock import MagicMock
from src.network.connection_message import MessageMixin

class DummyMessage(MessageMixin):
    def __init__(self):
        self.connected = False
        self.peer_socket = None
        self.crypto = MagicMock()
        self._ping_lock = MagicMock()
        self._ping_responses = {}
        self.message_callback = MagicMock()
        self.send_message = MagicMock()
    def _send_raw(self, data):
        pass

def test_handle_ping():
    obj = DummyMessage()
    handled = obj._handle_ping_pong("__PING__1234")
    assert handled
    obj.send_message.assert_called_with("__PONG__1234")

def test_handle_pong():
    obj = DummyMessage()
    obj._ping_responses = {"1234": None}
    handled = obj._handle_ping_pong("__PONG__1234")
    assert handled

def test_send_message_not_connected():
    obj = DummyMessage()
    obj.send_message("hello")  # Doit ne rien faire (pas d'exception) 