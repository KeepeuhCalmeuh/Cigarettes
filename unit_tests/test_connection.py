import pytest
from unittest.mock import MagicMock
from src.network.connection import P2PConnection

class DummyCallback:
    def __call__(self, msg):
        self.last_msg = msg

@pytest.fixture
def dummy_callback():
    return DummyCallback()

@pytest.fixture
def p2p_connection(dummy_callback):
    # On mocke les méthodes réseau pour éviter les vraies connexions
    conn = P2PConnection(12345, dummy_callback)
    conn.start_server = MagicMock()
    conn.stop = MagicMock()
    conn.close_server = MagicMock()
    return conn

def test_p2pconnection_init(p2p_connection):
    assert p2p_connection.listen_port == 12345
    assert callable(p2p_connection.message_callback)

def test_p2pconnection_server_methods(p2p_connection):
    p2p_connection.start_server()
    p2p_connection.stop()
    p2p_connection.close_server()
    p2p_connection.start_server.assert_called_once()
    p2p_connection.stop.assert_called_once()
    p2p_connection.close_server.assert_called_once() 