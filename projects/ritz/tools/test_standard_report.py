"""Tests for tools/standard_report.py (AGAST #1344).

docs/STANDARD.md's idiom rules (bool, Result, Option, raw pointers, impl,
ownership, aborting) are ADVISORY: no compiler refuses a violation yet. What
makes them more than opinion is that each one names a counting rule here, so
"how many violations does ritzlib have" is a command, not an argument
(#1344 acceptance; #1347 converts ritzlib against these counts).

One row per counting rule, each with the shape it must catch and the nearest
shape it must not; then the exemption syntax and the tree walk.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from standard_report import RULES, scan_source, scan_tree, summarise

pytestmark = pytest.mark.unit

TOOL = Path(__file__).with_name("standard_report.py")
STANDARD = Path(__file__).resolve().parent.parent / "docs" / "STANDARD.md"


def keys(text, path="lib/m.ritz"):
    """The (key, fn) of every non-exempt site in `text`."""
    return sorted((s.key, s.fn) for s in scan_source(text, path) if s.exempt is None)


# ---------------------------------------------------------------------------
# One row per counting rule: (source, expected non-exempt sites).
# Each rule has a hit and its nearest miss.
# ---------------------------------------------------------------------------

CASES = {
    # S-BOOL-2: a predicate's name, an integer return.
    "bool-return hit": (
        "pub fn str_is_empty(s: StrView) -> i32\n    0\n",
        [("bool-return", "str_is_empty")],
    ),
    "bool-return streq hit": (
        "pub fn streq(a: StrView, b: StrView) -> i32\n    0\n",
        [("bool-return", "streq")],
    ),
    "bool-return miss: returns bool": (
        "pub fn str_is_empty(s: StrView) -> bool\n    false\n",
        [],
    ),
    "bool-return miss: not a predicate name": (
        "pub fn str_len(s: StrView) -> i64\n    0\n",
        [],
    ),
    # S-RESULT-1: an integer return with a negative literal returned.
    "sentinel-return hit": (
        "pub fn find(s: StrView, c: u8) -> i64\n    if s.len == 0\n        return -1\n    0\n",
        [("sentinel-return", "find")],
    ),
    "sentinel-return miss: no negative return": (
        "pub fn find(s: StrView, c: u8) -> i64\n    let d = 0 - 1\n    return 0\n",
        [],
    ),
    # S-OPTION-1: a pointer or reference return with `return null`.
    "null-return hit": (
        "pub fn lookup(k: i64) -> *u8\n    return null\n",
        [("null-return", "lookup")],
    ),
    "null-return miss: Option": (
        "pub fn lookup(k: i64) -> Option<i64>\n    return None\n",
        [],
    ),
    # S-PTR-1: a raw pointer parameter on a public fn.
    "raw-ptr-param hit": (
        "pub fn put(p: *Point, v: i32)\n    pass\n",
        [("raw-ptr-param", "put")],
    ),
    "raw-ptr-param miss: reference": (
        "pub fn put(p: @&Point, v: i32)\n    pass\n",
        [],
    ),
    "raw-ptr-param miss: private fn": (
        "fn put(p: *Point, v: i32)\n    pass\n",
        [],
    ),
    # S-PTR-2: (*T, length) where a Span<T> or StrView belongs. Also a raw
    # pointer, so it counts under S-PTR-1 as well.
    "ptr-len-param hit": (
        "pub fn sum(xs: *i32, len: i64) -> i64\n    0\n",
        [("ptr-len-param", "sum"), ("raw-ptr-param", "sum")],
    ),
    "ptr-len-param hit, multi-line signature": (
        "pub fn write_all(\n    fd: i32,\n    buf: *u8,\n    n: i64\n) -> i64\n    0\n",
        [("ptr-len-param", "write_all"), ("raw-ptr-param", "write_all")],
    ),
    "ptr-len-param miss: Span": (
        "pub fn sum(xs: Span<i32>) -> i64\n    0\n",
        [],
    ),
    # S-IMPL-1: a public free fn whose first parameter is a type this file
    # declares. Constructors (no such parameter) and methods are fine.
    "free-fn-method hit": (
        "struct Counter\n    n: i64\n\npub fn counter_bump(c: @&Counter)\n    c.n += 1\n",
        [("free-fn-method", "counter_bump")],
    ),
    "free-fn-method hit through generics": (
        "struct Box<T>\n    p: *T\n\npub fn box_get<T>(b: @Box<T>) -> T\n    *b.p\n",
        [("free-fn-method", "box_get")],
    ),
    "free-fn-method miss: constructor": (
        "struct Counter\n    n: i64\n\npub fn counter_new() -> Counter\n    Counter { n: 0 }\n",
        [],
    ),
    "free-fn-method miss: method": (
        "struct Counter\n    n: i64\n\nimpl Counter\n    pub fn bump(self:&)\n        self.n += 1\n",
        [],
    ),
    "free-fn-method miss: type from another module": (
        "pub fn string_bump(s: @&String)\n    pass\n",
        [],
    ),
    # S-OWN-2: raw allocation outside the functions of the owning type.
    "raw-alloc hit": (
        "fn scratch(n: i64) -> i64\n    let p = malloc(n)\n    free(p)\n    n\n",
        [("raw-alloc", "scratch"), ("raw-alloc", "scratch")],
    ),
    "raw-alloc miss: owning type's constructor": (
        "struct Buf\n    p: *u8\n\nfn buf_new(n: i64) -> Buf\n    Buf { p: malloc(n) }\n",
        [],
    ),
    "raw-alloc miss: Drop": (
        "struct Buf\n    p: *u8\n\nimpl Drop for Buf\n    fn drop(self: @&Buf)\n        free(self.p)\n",
        [],
    ),
    "raw-alloc miss: a longer name, heap_free": (
        "fn scratch(p: *u8) -> i64\n    my_free(p)\n    0\n",
        [],
    ),
    # S-ERR-3: a library ends the program.
    "lib-exit hit": (
        "fn bail()\n    sys_exit(1)\n",
        [("lib-exit", "bail")],
    ),
    "lib-exit miss: main": (
        "fn main() -> i32\n    sys_exit(1)\n    0\n",
        [],
    ),
    # Never: comments, strings, tests, extern declarations.
    "miss: in a comment or string": (
        'fn f() -> i32\n    # malloc(4) and sys_exit(1)\n    let s = "free(p)"\n    0\n',
        [],
    ),
    "miss: a [[test]] fn": (
        "[[test]]\nfn test_x() -> i32\n    sys_exit(1)\n    0\n",
        [],
    ),
    "miss: trait impl signature": (
        "struct M\n    n: i64\n\nimpl Index for M\n    pub fn index(self: @M, k: i64) -> @i64\n        return null\n",
        [],
    ),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_counting_rule(name):
    text, want = CASES[name]
    assert keys(text) == sorted(want)


def test_site_carries_line_and_path():
    text = "\n\npub fn lookup(k: i64) -> *u8\n    return null\n"
    (site,) = scan_source(text, "lib/x.ritz")
    assert (site.path, site.line, site.fn, site.key) == ("lib/x.ritz", 3, "lookup", "null-return")


# ---------------------------------------------------------------------------
# Exemptions: documented in the module, with a reason (#1347 acceptance).
# ---------------------------------------------------------------------------


def test_fn_exemption_needs_key_and_reason():
    text = (
        "# Write to fd.\n"
        "# standard-exempt: raw-ptr-param, ptr-len-param: the write(2) ABI\n"
        "pub fn sys_write(fd: i32, buf: *u8, n: i64) -> i64\n    0\n"
    )
    sites = scan_source(text, "lib/sys.ritz")
    assert {s.key for s in sites} == {"raw-ptr-param", "ptr-len-param"}
    assert all(s.exempt == "the write(2) ABI" for s in sites)


def test_exemption_covers_only_its_keys():
    text = (
        "# standard-exempt: raw-ptr-param: the write(2) ABI\n"
        "pub fn sys_write(fd: i32, buf: *u8, n: i64) -> i64\n    0\n"
    )
    assert keys(text) == [("ptr-len-param", "sys_write")]


def test_exemption_must_touch_the_fn():
    text = (
        "# standard-exempt: raw-ptr-param: the write(2) ABI\n"
        "\n"
        "pub fn put(p: *u8)\n    pass\n"
    )
    assert keys(text) == [("raw-ptr-param", "put")]


def test_exemption_without_reason_is_itself_a_violation():
    text = "# standard-exempt: raw-ptr-param: abi\npub fn put(p: *u8)\n    pass\n"
    assert keys(text) == [("exempt-malformed", "put"), ("raw-ptr-param", "put")]


def test_exemption_with_unknown_key_is_a_violation():
    text = "# standard-exempt: raw-pointer: the write(2) ABI\npub fn put(p: *u8)\n    pass\n"
    assert ("exempt-malformed", "put") in keys(text)


def test_file_exemption():
    text = (
        "# memory.ritz - the allocator\n"
        "# standard-exempt-file: raw-alloc: this module is the allocator\n"
        "\n"
        "fn grab(n: i64) -> *u8\n    malloc(n)\n"
    )
    (site,) = scan_source(text, "lib/memory.ritz")
    assert site.key == "raw-alloc" and site.exempt == "this module is the allocator"


# ---------------------------------------------------------------------------
# The tree walk, the summary and the CLI.
# ---------------------------------------------------------------------------


def test_tree_skips_test_directories(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.ritz").write_text("pub fn f(p: *u8)\n    pass\n")
    (tmp_path / "a.ritz").write_text("pub fn g(p: *u8)\n    pass\n")
    assert [s.fn for s in scan_tree([tmp_path])] == ["g"]


def test_summary_counts_violations_and_exemptions():
    text = (
        "# standard-exempt: raw-ptr-param: the write(2) ABI\n"
        "pub fn a(p: *u8)\n    pass\n"
        "pub fn b(p: *u8)\n    pass\n"
    )
    summary = summarise(scan_source(text, "m.ritz"))
    assert summary["raw-ptr-param"] == {"violations": 1, "exempt": 1}
    assert summary["null-return"] == {"violations": 0, "exempt": 0}


@pytest.mark.integration
def test_cli_json_and_list(tmp_path):
    (tmp_path / "a.ritz").write_text("pub fn lookup(k: i64) -> *u8\n    return null\n")
    out = subprocess.run(
        [sys.executable, str(TOOL), "--json", str(tmp_path)],
        capture_output=True, text=True, check=True,
    ).stdout
    assert json.loads(out)["null-return"] == {"violations": 1, "exempt": 0}
    listing = subprocess.run(
        [sys.executable, str(TOOL), "--list", "null-return", str(tmp_path)],
        capture_output=True, text=True, check=True,
    ).stdout
    assert "a.ritz:1" in listing and "lookup" in listing


# ---------------------------------------------------------------------------
# Converted module groups (#1347).  Each group that has been driven to zero is
# pinned here, so a new raw `*T` parameter has to be converted or exempted with
# a reason deliberately rather than landing quietly.  The whole tree is still
# being converted, so the pin is per module, not tree-wide.
# ---------------------------------------------------------------------------

RITZ_ROOT = Path(__file__).resolve().parent.parent


def test_json_module_has_no_raw_pointer_parameters():
    """AGAST #4446: json's API takes references, Span and StrView."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "json.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}


def test_str_module_has_no_raw_pointer_parameters():
    """AGAST #4534: str is C-string interop only; every raw *u8 is a C ABI.

    The two functions with a StrView/String equivalent and no callers
    (strrchr, strncpy) were deleted; the remaining 25 raw pointer parameters
    across 15 functions are exempted against the C ABI they exist to serve.
    strchr and strstr stay because nexus/zeus test suites still call them.
    """
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "str.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 25}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}


# AGAST #4539: the remaining module groups (#1347 continuation).  Each
# parameter that is not a raw boundary takes a reference or a span; the rest
# are exempt against the C/allocator/sink ABI they exist to serve.  A new raw
# `*T` here must be converted or exempted with a reason deliberately.
RAW_PTR_PARAM_FREE_MODULES = {
    "async/blocking_fs.ritz": 4,  # NUL-terminated paths handed to open(2)
    "async/tasks.ritz": 0,
    "async_net.ritz": 0,
    "box.ritz": 1,  # allocator
    "elf.ritz": 7,  # ELF image / .strtab / callback ABI
    "fmt/digits.ritz": 4,  # fixed-size digit buffer sink
    "fmt/impls.ritz": 3,  # NUL-terminated C string Display impls
    "fmt/writer.ritz": 2,  # compiler-emitted sink protocol
    "hashmap.ritz": 4,  # allocator
    "io.ritz": 4,  # NUL-terminated C string printers
    "iovec.ritz": 0,
    "memory.ritz": 8,  # the allocator itself
    "os/env.ritz": 1,  # execve(2) envp
    "process.ritz": 0,
    "ptr.ritz": 1,  # the raw-pointer primitive
    "testlib.ritz": 9,  # C strings / execve(2) ABI
    "timer.ritz": 0,
}


@pytest.mark.parametrize("module,exempt", sorted(RAW_PTR_PARAM_FREE_MODULES.items()))
def test_module_has_no_raw_pointer_parameters(module, exempt):
    """AGAST #4539: every raw *T parameter is converted or exempted with a reason."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / module]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": exempt}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}


def test_every_counting_rule_names_a_rule_in_the_standard():
    """A key here points at a rule ID in docs/STANDARD.md, and the doc names the key."""
    doc = STANDARD.read_text()
    for key, (rule_id, _) in RULES.items():
        assert f"#### {rule_id} " in doc, f"{key}: {rule_id} is not a rule in STANDARD.md"
        assert f"`{key}`" in doc, f"{key} is not named in STANDARD.md"

