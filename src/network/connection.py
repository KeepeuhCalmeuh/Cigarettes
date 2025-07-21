"""
P2P connection management for secure peer-to-peer communication.
Handles connection establishment, message exchange, and file transfers.
"""

import socket
import threading
import json
import time
from typing import Callable, Optional, Tuple
from datetime import datetime
import ipaddress
import os
from colorama import Fore, Style
import socks

from .connection_base import P2PConnection as P2PConnectionBase
from .connection_handshake import HandshakeMixin
from .connection_peer import PeerMixin
from .connection_message import MessageMixin
from .connection_file import FileTransferMixin
from .connection_io import IOMixin


class P2PConnection(HandshakeMixin, PeerMixin, MessageMixin, FileTransferMixin, IOMixin, P2PConnectionBase):
    """
    Manages P2P connections with encryption, authentication, and file transfer capabilities.
    (Héritage multiple de mixins)
    """
    pass