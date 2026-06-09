import sys
from pathlib import Path

# Make the project root importable (shell.py, repair.py, voxel.py, ...).
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
