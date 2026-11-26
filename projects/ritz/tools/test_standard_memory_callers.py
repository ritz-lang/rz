"""AGAST #4638: raw memory calls outside ritzlib, per project, pinned down-only.

Goal 5's memory slice of #4636's caller ratchet (tools/test_standard_callers.py
pins every exempt raw API together). This pins only the allocator and mmap
boundary: malloc/free/realloc/calloc, memzero/secure_zero, heap_alloc/
heap_free, mmap_failed and sys_mmap/sys_munmap. Their idiomatic replacements:

* an owned buffer: `Vec<u8>` / `Box<T>` / `String` (ritz1 waits on #1854's
  Drop, so ownership doesn't turn its leaks into double frees);
* `span.zero()` / `span.secure_zero()` for memzero(p, n) / secure_zero(p, n);
* ritzlib.mapping's `mmap_anon(len) -> Result<Span<u8>, Errno>` and
  `munmap(span)` for sys_mmap / sys_munmap.

`ritz` is split by its top directory (examples, ritz1, ...): they are ported
separately. Each count is a ceiling: lower the pin when you port callers.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from standard_report import count_callers, exempt_apis

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent
PROJECTS = RITZ_ROOT.parent

MEMORY_APIS = frozenset({
    "malloc", "free", "realloc", "calloc", "memzero", "secure_zero",
    "heap_alloc", "heap_free", "mmap_failed", "sys_mmap", "sys_munmap",
})

PINS = {
    "angelo": 4,
    "cryptosec": 0,
    "indium": 16,
    "lexis": 6,
    "prism": 3,
    "ritz/ritz0": 18,
    "ritz/ritz1": 511,
    "ritzunit": 7,
    "rzsh": 4,
}


def memory_callers_by_project(sites, root):
    """{project: calls} of MEMORY_APIS; `ritz` keyed as ritz/<top dir>."""
    out = {}
    for s in sites:
        if s.api not in MEMORY_APIS:
            continue
        parts = Path(s.path).relative_to(root).parts
        key = parts[0] if parts[0] != "ritz" else f"ritz/{parts[1]}"
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def memory_apis(lib):
    """{api: {module}} for MEMORY_APIS: the exempt ones as --callers sees
    them, plus sys_mmap, which is raw (-errno in a pointer) but not exempt."""
    apis = {k: v for k, v in exempt_apis(lib).items() if k in MEMORY_APIS}
    apis.setdefault("sys_mmap", set()).add("sys")
    return apis


@pytest.fixture(scope="module")
def by_project():
    lib = RITZ_ROOT / "ritzlib"
    return memory_callers_by_project(count_callers(lib, [PROJECTS], memory_apis(lib)), PROJECTS)


def test_raw_memory_callers_only_go_down(by_project):
    over = {p: (n, PINS.get(p, 0)) for p, n in by_project.items() if n > PINS.get(p, 0)}
    assert over == {}, f"project: (calls, pin) over the pin: {over}"


def test_memory_apis_are_all_counted():
    """Every pinned API resolves to a ritzlib module: one that lost its
    exemption (or was renamed) would silently drop out of the pin."""
    missing = MEMORY_APIS - set(memory_apis(RITZ_ROOT / "ritzlib"))
    assert missing == set(), f"not counted: {sorted(missing)}"


def test_split_keys_ritz_by_top_directory(tmp_path):
    from standard_report import CallSite
    sites = [CallSite("malloc", str(tmp_path / "ritz" / "ritz1" / "a.ritz"), 1),
             CallSite("free", str(tmp_path / "tome" / "src" / "b.ritz"), 2),
             CallSite("sys_write", str(tmp_path / "tome" / "src" / "b.ritz"), 3)]
    assert memory_callers_by_project(sites, tmp_path) == {"ritz/ritz1": 1, "tome": 1}
