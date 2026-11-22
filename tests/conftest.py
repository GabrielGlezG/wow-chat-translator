import sys
from pathlib import Path

# Asegurar que la raíz del proyecto esté siempre en sys.path al correr pytest
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
