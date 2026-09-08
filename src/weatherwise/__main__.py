"""
Execution entry point for python -m weatherwise.
"""

from __future__ import annotations

import sys

from weatherwise.cli import main

if __name__ == "__main__":
    sys.exit(main())
