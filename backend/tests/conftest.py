# tests/conftest.py
# Author: Suresh D R | AI Product Developer & Technology Mentor

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("OPENAI_API_KEY", "sk-test-placeholder")
os.environ.setdefault("RDS_HOST", "localhost")
os.environ.setdefault("RDS_PASSWORD", "test")
os.environ.setdefault("CACHE_ENABLED", "false")
