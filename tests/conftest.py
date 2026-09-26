"""
tests/conftest.py
Pytest configuration — ensures the project root is on sys.path.
"""
import sys
from pathlib import Path

# Add project root to sys.path so imports like `from security.gate import ...` work
sys.path.insert(0, str(Path(__file__).parent.parent))
