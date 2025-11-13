import pytest
from unittest.mock import MagicMock, patch
import src.ui.command_handlers as handlers

def test_dummy():
    assert True

# Ajoute ici tes tests pour command_handlers.py 

@patch('builtins.print')
def test_handle_connect_command_usage(mock_print):
    ui = MagicMock()
    handlers.handle_connect_command(ui, ['/connect'])
    mock_print.assert_called_with('Usage: /connect <peer_onion_address> <PEER_FINGERPRINT> [port]')

@patch('builtins.print')
def test_handle_status_command_not_connected(mock_print):
    ui = MagicMock()
    ui.connection = None
    handlers.handle_status_command(ui)
    mock_print.assert_called_with('No connection manager available.')

@patch('builtins.print')
def test_handle_save_command_no_history(mock_print):
    ui = MagicMock()
    ui.history = []
    handlers.handle_save_command(ui)
    mock_print.assert_called_with('No conversation history to save.')

@patch('builtins.print')
def test_handle_exit_command(mock_print):
    ui = MagicMock()
    ui.connection = None
    ui._stop_flag = MagicMock()
    handlers.handle_exit_command(ui)
    mock_print.assert_any_call('Exiting...')
    ui._stop_flag.set.assert_called_once() 