import sys
from pathlib import Path

# Add root directory to sys.path so modules like main, database, rules_engine import cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import app
