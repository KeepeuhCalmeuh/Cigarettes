import pytest
from unittest.mock import patch
import sys
from src.main import validate_port

def test_dummy():
    assert True

# Ajoute ici tes tests pour main.py 

@patch('builtins.print')
def test_validate_port_valid(mock_print):
    assert validate_port('34567') == 34567

@patch('builtins.print')
def test_validate_port_invalid(mock_print):
    with pytest.raises(ValueError):
        validate_port('bad')
    with pytest.raises(ValueError):
        validate_port('80')

@patch('src.main.print_banner')
@patch('builtins.print')
def test_main_usage_and_error(mock_print, mock_banner):
    import src.main as main_mod
    sys_argv_backup = sys.argv
    sys.argv = ['main.py', 'badport']
    with patch('src.main.launch_tor_with_hidden_service', side_effect=Exception('fail')):
        main_mod.main()
    sys.argv = sys_argv_backup 