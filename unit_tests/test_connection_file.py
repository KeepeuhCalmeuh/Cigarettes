import pytest
from unittest.mock import MagicMock
from src.network.connection_file import FileTransferMixin

class DummyFileTransfer(FileTransferMixin):
    def __init__(self):
        self.message_callback = MagicMock()
        self.send_message = MagicMock()
        self.crypto = MagicMock()
        self._pending_file_path = None
    def _send_raw(self, data):
        pass
    def _receive_raw(self):
        return b''

def test_send_file_not_found(tmp_path):
    obj = DummyFileTransfer()
    obj.send_file(str(tmp_path / 'nofile.txt'))
    obj.message_callback.assert_called_with('File not found: ' + str(tmp_path / 'nofile.txt'))

def test_handle_file_request():
    obj = DummyFileTransfer()
    msg = "__FILE_REQUEST__{'file_name': 'test.txt', 'file_size': 123}"
    handled = obj._handle_file_transfer(msg)
    assert handled
    obj.message_callback.assert_any_call('Peer wants to send you a file: test.txt (123 bytes)') 