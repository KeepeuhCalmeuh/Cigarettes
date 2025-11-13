import pytest
from unittest.mock import MagicMock, patch
from src.ui.console_ui import ConsoleUI

@patch('builtins.print')
def test_console_ui_init(mock_print):
    ui = ConsoleUI()
    assert ui.connection is None
    assert hasattr(ui, 'hosts_manager')
    assert isinstance(ui.history, list)
    assert not ui._multiline_mode

@patch('builtins.print')
def test_display_help(mock_print):
    ui = ConsoleUI()
    ui.display_help()
    # Vérifie que print a été appelé (aide affichée)
    assert mock_print.called

@patch('builtins.print')
def test_handle_message_disconnect(mock_print):
    ui = ConsoleUI()
    ui.connection = MagicMock()
    ui.display_help = MagicMock()
    ui._display_prompt = MagicMock()
    ui.handle_message("__DISCONNECT__")
    ui.connection.stop.assert_called_once()
    ui.display_help.assert_called_once()
    ui._display_prompt.assert_called_once()
    assert mock_print.called

def test_multiline_mode():
    ui = ConsoleUI()
    assert not ui._multiline_mode
    ui._multiline_mode = True
    assert ui._multiline_mode 