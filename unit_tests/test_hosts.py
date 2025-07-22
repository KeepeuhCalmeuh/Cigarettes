import pytest
import os
from src.core.hosts import KnownHostsManager

def test_dummy():
    assert True

# Ajoute ici tes tests pour hosts.py 

def test_add_and_remove_host(tmp_path):
    hosts_file = tmp_path / 'hosts.json'
    mgr = KnownHostsManager(str(hosts_file))
    addr = '1.2.3.4:1234'
    fp = 'a'*64
    assert mgr.add_host(addr, fp)
    assert mgr.get_host_fingerprint(addr) == fp
    assert mgr.remove_host(addr)
    assert mgr.get_host_fingerprint(addr) is None

def test_set_and_get_nickname(tmp_path):
    hosts_file = tmp_path / 'hosts.json'
    mgr = KnownHostsManager(str(hosts_file))
    fp = 'b'*64
    mgr.set_nickname(fp, 'bob')
    assert mgr.get_nickname(fp) == 'bob'

def test_validate_fingerprint():
    mgr = KnownHostsManager('/dev/null')
    assert mgr._validate_fingerprint('a'*64)
    assert not mgr._validate_fingerprint('bad')

def test_validate_ip_and_onion_address():
    mgr = KnownHostsManager('/dev/null')
    assert mgr._validate_ip_address('1.2.3.4:1234')
    assert not mgr._validate_ip_address('1.2.3.4')
    assert mgr._validate_onion_address('abc.onion:1234')
    assert not mgr._validate_onion_address('abc.com:1234') 