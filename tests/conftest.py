"""Pytest configuration and fixtures."""
import sys
from pathlib import Path

# Add the project root to the Python path so tests can import backend
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables for testing
import os
os.environ.setdefault("TESTING", "True")
