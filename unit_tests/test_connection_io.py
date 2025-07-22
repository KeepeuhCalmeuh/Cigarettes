import pytest
from src.network.connection_io import IOMixin

class DummyIO(IOMixin):
    def __init__(self):
        self.peer_socket = None

def test_send_raw_no_socket():
    obj = DummyIO()
    # Doit simplement ne rien faire, pas d'exception
    obj._send_raw(b'data')

def test_receive_raw_no_socket():
    obj = DummyIO()
    assert obj._receive_raw() == b'' 