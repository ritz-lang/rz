"""Harland's results mean something, its flags are bools, one strlen (AGAST #4600).

LARB v4 (review/4/harland.md, M10; the rest of #1885) found in kernel/src
and boot/src:

  - ~99 `-> i32` functions whose every result is 0. A caller can learn
    nothing from them, and some checked it anyway. They return nothing now;
    projects/harland/tools/always_zero.py counts what is left, and its
    ALLOWED names each one that stays, with why (kernel_main for #1887; six
    declared through cycle-breaking externs for #4625).
  - ~34 `var x: u8 = 0` globals, most of them flags written only 0 and 1 and
    compared only with 0 and 1. Those are `bool`.
  - syscall_strlen and open-coded `while *(p + n) != 0` length loops beside
    ritzlib.str.strlen.
  - the cwd as a bare `[256]u8` plus a separate length. It is a Cwd holder
    in proc/table.ritz, read as a StrView (proc_cwd) and written from one
    (proc_set_cwd); test_harland_process_model.py runs it.

These read harland's source. Runs in `make tools-unit`.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HARLAND = Path(__file__).resolve().parents[2] / "harland"
TREES = ["kernel/src", "boot/src"]


def _always_zero():
    path = HARLAND / "tools" / "always_zero.py"
    spec = importlib.util.spec_from_file_location("harland_always_zero", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


AZ = _always_zero()


def _sources():
    for tree in TREES:
        yield from sorted((HARLAND / tree).rglob("*.ritz"))


def _code_lines(path):
    """(n, line) for each line of path that isn't blank or a comment."""
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if s and not s.startswith("#"):
            yield n, line


# ---------------------------------------------------------------------------
# always-0 `-> i32` fns
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src, want", [
    ("fn f() -> i32\n    g()\n    return 0\n", ["f"]),
    ("fn f() -> i32\n    g()\n    0\n", ["f"]),
    ("fn f(x: bool) -> i32\n    if x\n        return 0\n    return 0\n", ["f"]),
    ("fn f(x: bool) -> i32\n    if x\n        return -1\n    return 0\n", []),
    ("fn f() -> i32\n    return g()\n", []),
    ("fn f() -> i32\n    g()\n", []),                  # tail is g's value
    ("fn f() -> i64\n    return 0\n", []),             # i32 only
    ("extern fn f() -> i32\nfn h()\n    g()\n", []),
    ("pub fn f() -> i32  # note\n    return 0  # done\n", ["f"]),
])
def test_scanner_finds_fns_whose_every_result_is_zero(src, want):
    assert [name for _, name in AZ.always_zero_fns(src)] == want


def test_always_zero_fns_are_only_the_allowed_ones():
    hits = AZ.scan()
    names = {h.rsplit(": ", 1)[1] for h in hits}
    assert [h for h in hits if h.rsplit(": ", 1)[1] not in AZ.ALLOWED] == [], (
        "these `-> i32` fns only ever return 0: make them return nothing, "
        "or list one in tools/always_zero.py ALLOWED with why")
    assert sorted(set(AZ.ALLOWED) - names) == [], (
        "no longer always-0: drop them from ALLOWED")


def test_acceptance_fewer_than_twenty():
    assert len(AZ.scan()) < 20


# ---------------------------------------------------------------------------
# u8 globals used as booleans
# ---------------------------------------------------------------------------

U8_GLOBAL = re.compile(r"^var (\w+): u8 = [01]\b")


def _flag_shaped_u8_globals():
    """'path:line: name' for each `var x: u8 = 0|1` global that is only ever
    set to 0 or 1 and only compared with 0 or 1, in the whole tree."""
    sources = list(_sources())
    texts = {p: [line for _, line in _code_lines(p)] for p in sources}
    out = []
    for path in sources:
        for n, line in _code_lines(path):
            m = U8_GLOBAL.match(line)
            if not m:
                continue
            name = m.group(1)
            ref = re.compile(r"(?<![\w.])" + name + r"(?!\w)")
            flag_use = re.compile(r"(?<![\w.])" + name + r"\s*(?:=|==|!=)\s*[01]\b(?!\s*[-+*/&|<>])")
            uses = [ln for lines in texts.values() for ln in lines
                    if ref.search(ln) and not U8_GLOBAL.match(ln)]
            if uses and all(len(ref.findall(ln)) == len(flag_use.findall(ln)) for ln in uses):
                out.append(f"{path.relative_to(HARLAND)}:{n}: {name}")
    return out


def test_no_u8_global_is_a_flag():
    assert _flag_shaped_u8_globals() == [], "set only to 0/1, compared only with 0/1: make it bool"


def test_flag_detector_sees_a_flag(tmp_path, monkeypatch):
    tree = tmp_path / "kernel" / "src"
    tree.mkdir(parents=True)
    (tree / "a.ritz").write_text(
        "var on: u8 = 0\nvar mode: u8 = 0\n"
        "fn f()\n    on = 1\n    mode = 2\n    if on != 0 and mode == 1\n        on = 0\n")
    monkeypatch.setattr(sys.modules[__name__], "HARLAND", tmp_path)
    assert _flag_shaped_u8_globals() == ["kernel/src/a.ritz:1: on"]


# ---------------------------------------------------------------------------
# one strlen
# ---------------------------------------------------------------------------

# `while *p != 0` or `while *(p + n) != 0`, optionally `and <bound>`.
NUL_SCAN = re.compile(r"^(\s*)while \*\(?\s*(\w+)(?:\s*\+\s*(\w+))?\s*\)? != 0(?: and \w+ < \w+)?\s*$")
STEP = re.compile(r"^\s*(\w+)\s*(?:=\s*\1\s*\+\s*1|\+=\s*1)\s*$")


def _open_coded_strlens():
    """'path:line' for each NUL-scanning while whose body only steps a counter."""
    out = []
    for path in _sources():
        lines = list(_code_lines(path))
        for i, (n, line) in enumerate(lines):
            m = NUL_SCAN.match(line)
            if not m:
                continue
            indent = len(m.group(1))
            body = []
            for _, nxt in lines[i + 1:]:
                if len(nxt) - len(nxt.lstrip(" ")) <= indent:
                    break
                body.append(nxt)
            if body and all(STEP.match(b) for b in body):
                out.append(f"{path.relative_to(HARLAND)}:{n}")
    return out


def test_no_open_coded_strlen():
    assert _open_coded_strlens() == [], "use ritzlib.str.strlen"


def test_no_syscall_strlen():
    hits = [f"{p.relative_to(HARLAND)}:{n}" for p in _sources()
            for n, line in _code_lines(p) if re.search(r"\bsyscall_strlen\b", line)]
    assert hits == []


# ---------------------------------------------------------------------------
# the cwd holder
# ---------------------------------------------------------------------------

def test_cwd_is_a_holder_read_as_a_strview():
    table = (HARLAND / "kernel" / "src" / "proc" / "table.ritz").read_text()
    assert re.search(r"^pub struct Cwd\n    bytes: \[256\]u8\n    len: u16$", table, re.M)
    assert re.search(r"^    cwd: Cwd\b", table, re.M)
    assert not re.search(r"^\s+cwd_len\b", table, re.M)
    assert re.search(r"^pub fn proc_cwd\(\) -> StrView$", table, re.M)
    assert re.search(r"^pub fn proc_set_cwd\(path: StrView\) -> i32$", table, re.M)
