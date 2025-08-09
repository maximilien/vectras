import os
import sys
from pathlib import Path

# Ensure src/ is on the path for tests
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
os.environ.setdefault("PYTHONPATH", str(SRC_PATH))
