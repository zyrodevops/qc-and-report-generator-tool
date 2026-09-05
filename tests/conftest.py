"""
Root pytest configuration and custom markers.
"""

import sys
from pathlib import Path
import pytest

# Ensure backend root is on sys.path for canonical 'app' imports
backend_root = Path(__file__).resolve().parent.parent / "backend"
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))


def pytest_configure(config):
    config.addinivalue_line("markers", "m1: Milestone 1 - Scaffold & Persistence")
    config.addinivalue_line("markers", "m2: Milestone 2 - Core Domain & Ingestion")
    config.addinivalue_line("markers", "m3: Milestone 3 - Document & Media Engine")
    config.addinivalue_line("markers", "m4: Milestone 4 - Corpus Mining Tool")
    config.addinivalue_line("markers", "m5: Milestone 5 - User Interface")
    config.addinivalue_line("markers", "tier1: Tier 1 - Feature Coverage")
    config.addinivalue_line("markers", "tier2: Tier 2 - Boundary & Corner Cases")
    config.addinivalue_line("markers", "tier3: Tier 3 - Cross-Feature Combinations")
    config.addinivalue_line("markers", "tier4: Tier 4 - Real-World Application Scenarios")
