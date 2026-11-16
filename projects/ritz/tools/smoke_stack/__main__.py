"""`python3 projects/ritz/tools/smoke_stack [SUITE...]` (CI's build-all runs this).

Run as a directory, Python puts this package's own directory first on
sys.path; the package's parent (tools/) goes there instead so its relative
imports resolve as `smoke_stack.*`. Exits 0 or 1 only: ci_local reads 3 as
a SETUP ERROR.
"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path[0] = str(Path(__file__).resolve().parent.parent)

from smoke_stack.cli import main

if __name__ == "__main__":
    sys.exit(main())
