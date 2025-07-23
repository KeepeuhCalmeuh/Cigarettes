#!/usr/bin/env python3
"""
Main entry point for the Cigarettes P2P chat application.
This is the new modular version that uses the reorganized code structure.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import main

if __name__ == "__main__":
    main() 