"""AGAST #3632: no function in build.py's modules or `rz` is over the
150 SLOC / cyclomatic-complexity 30 limit, measured by ritz-metrics.

build_package (162 SLOC, CC 37) was the last one over; it is now a loop over
per-target helpers. This keeps the next one from growing back past it.
"""

import functools
import importlib.util
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
REPO = PKG_DIR.parents[1]
METRICS_PY = REPO / "projects" / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"

MAX_SLOC = 150
MAX_CC = 30

FILES = [PKG_DIR / f for f in ("build.py", "build_pipeline.py", "build_testrun.py",
                               "build_cli.py", "manifest.py", "resolve.py", "packages.py",
                               "bounded_run.py")] + [REPO / "rz"]


@functools.cache
def _metrics():
    spec = importlib.util.spec_from_file_location("ritz_metrics_for_build", METRICS_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod      # its dataclasses look their module up
    spec.loader.exec_module(mod)
    return mod


def oversized(path: Path) -> list[str]:
    fns = _metrics().extract_functions(path, path.read_text().splitlines(), "py")
    return [f"{path.name}:{f.line} {f.name}: {f.sloc} SLOC, CC {f.complexity}"
            for f in fns if f.sloc > MAX_SLOC or f.complexity > MAX_CC]


@pytest.mark.unit
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_function_over_the_limit(path):
    found = oversized(path)
    assert not found, (f"over {MAX_SLOC} SLOC / CC {MAX_CC}; split it:\n  "
                       + "\n  ".join(found))
