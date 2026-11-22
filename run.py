"""Lanzador principal independiente para WoW Chat Translator."""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from src.main import main

if __name__ == "__main__":
    sys.exit(main())
