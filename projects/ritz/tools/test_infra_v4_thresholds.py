"""AGAST #4606: infra functions LARB review/5 found over the v4 thresholds stay under them.

LARB v4 (projects/larb/review/INSTRUCTIONS_v4.md section 1) makes a function a
finding at SLOC > 150, cyclomatic complexity > 30 or nesting depth >= 6.
Review/5 (packages.md M8) listed these infra functions over that line:

  valet_handle_connection, valet_handle_tls_connection  (valet/lib/valet.ritz)
  handle_task_event_encrypted                            (mausoleum/lib/server_async.ritz)
  cmd_dispatch                                           (tome/lib/commands.ritz)
  qpack_static_get, get_k512, x509_parse_extensions      (already fixed: #1866, v5)

The state machines were split per state, and cmd_dispatch asks one
dispatch_<family> helper per command family (a const table can't hold fn
pointers, LANGUAGE_SPEC section 3.3), with no behaviour change: each package's own tests, on
ritz0 and ritz1, are the behaviour proof. This file measures them with the
LARB ritz-metrics script (it reads source; nothing compiles), so the next
feature is not bolted back onto one giant fn.

squeeze's deflate_dynamic, deferred while #4605 / #4611 reworked squeeze, was
split by AGAST #4624 into dyn_<phase> helpers (LZ77 pass, tree building,
code-length encoding, block emission); test_fixed_huffman_pin.ritz pins its
bytes at levels 1, 6 and 9.
"""

import functools
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / "projects"
METRICS_PY = PROJECTS / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"

# LARB v4 "major" line: over any of these is a finding by default.
MAX_SLOC = 150
MAX_CC = 30
MAX_DEPTH = 5  # depth >= 6 is over

PINNED = {
    "valet_handle_connection": "valet/lib/valet.ritz",
    "valet_handle_tls_connection": "valet/lib/valet.ritz",
    "handle_task_event_encrypted": "mausoleum/lib/server_async.ritz",
    "cmd_dispatch": "tome/lib/commands.ritz",
    "qpack_static_get": "http/lib/qpack_static.ritz",
    "x509_parse_extensions": "cryptosec/lib/x509.ritz",
    "deflate_dynamic": "squeeze/lib/deflate.ritz",
}

# Files whose every fn is held to the line: the split must not just move the
# bulk into one new helper.
WHOLE_FILE_HELPERS = {
    "valet/lib/valet.ritz": ("valet_",),
    "mausoleum/lib/server_async.ritz": ("handle_task_event_encrypted", "enc_"),
    "tome/lib/commands.ritz": ("cmd_dispatch", "dispatch_"),
    "squeeze/lib/deflate.ritz": ("deflate_dynamic", "dyn_"),
}


@functools.cache
def _metrics():
    spec = importlib.util.spec_from_file_location("ritz_metrics_4606", METRICS_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # its dataclasses look their module up
    spec.loader.exec_module(mod)
    return mod


@functools.cache
def _functions(rel):
    path = PROJECTS / rel
    return tuple(_metrics().extract_functions(path, path.read_text().splitlines(), "ritz"))


def _over(f):
    return f.sloc > MAX_SLOC or f.complexity > MAX_CC or f.max_depth > MAX_DEPTH


def _describe(rel, f):
    return f"{f.name} ({rel}:{f.line}) SLOC {f.sloc} CC {f.complexity} depth {f.max_depth}"


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(PINNED))
def test_pinned_function_under_v4_thresholds(name):
    rel = PINNED[name]
    fns = [f for f in _functions(rel) if f.name == name]
    assert len(fns) == 1, f"{rel}: expected one fn {name}, found {len(fns)}"
    assert not _over(fns[0]), (
        f"over the v4 thresholds (SLOC > {MAX_SLOC}, CC > {MAX_CC} or depth > {MAX_DEPTH}); "
        f"split it per state: {_describe(rel, fns[0])}")


@pytest.mark.unit
def test_get_k512_is_a_const_table():
    src = (PROJECTS / "cryptosec" / "lib" / "sha512.ritz").read_text()
    assert "const K512: [80]u64 = [" in src, "K512 is no longer a const [80]u64 table"
    assert "fn get_k512" not in src, "get_k512 ladder is back"


@pytest.mark.unit
@pytest.mark.parametrize("rel", sorted(WHOLE_FILE_HELPERS))
def test_split_helpers_under_v4_thresholds(rel):
    prefixes = WHOLE_FILE_HELPERS[rel]
    found = [_describe(rel, f) for f in _functions(rel)
             if f.name.startswith(prefixes) and _over(f)]
    assert not found, "over the v4 thresholds:\n  " + "\n  ".join(found)
