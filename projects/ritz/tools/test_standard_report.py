"""Tests for tools/standard_report.py (AGAST #1344).

docs/STANDARD.md's idiom rules (bool, Result, Option, raw pointers, impl,
ownership, aborting) are ADVISORY: no compiler refuses a violation yet. What
makes them more than opinion is that each one names a counting rule here, so
"how many violations does ritzlib have" is a command, not an argument
(#1344 acceptance; #1347 converts ritzlib against these counts).

One row per counting rule, each with the shape it must catch and the nearest
shape it must not; then the exemption syntax and the tree walk.

The per-module pins (the counts each converted module must hold) live in
test_standard_pins/, one file per module.  Add a new module pin as its own
new file there — never append it here (AGAST #4551).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from standard_report import (
    RULES,
    callers_by_project,
    count_callers,
    exempt_apis,
    ratchet_breaches,
    scan_source,
    scan_tree,
    summarise,
)

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
    # #4636: the C ctype names have no `_` to split on.
    "bool-return hit: isdigit": (
        "pub fn isdigit(c: u8) -> i32\n    0\n",
        [("bool-return", "isdigit")],
    ),
    "bool-return miss: isdigit returns bool": (
        "pub fn isdigit(c: u8) -> bool\n    false\n",
        [],
    ),
    "bool-return miss: an is-prefixed name with a digit or _": (
        "pub fn is2(c: u8) -> i32\n    0\npub fn isolate_x(c: u8) -> i32\n    0\n",
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
    # S-RESULT-2 (#4636): a bare integer status: a named negative code, or a
    # syscall's raw result passed straight through.
    "status-return hit: return -EINVAL": (
        "pub fn open_it(fd: i32) -> i32\n    if fd < 0\n        return -EINVAL\n    0\n",
        [("status-return", "open_it")],
    ),
    "status-return hit: syscallN passthrough": (
        "pub fn close_it(fd: i32) -> i32\n    return syscall1(3, fd as i64) as i32\n",
        [("status-return", "close_it")],
    ),
    "status-return hit: sys_* passthrough in a method": (
        (
            "struct R\n    fd: i32\n\nimpl R\n    pub fn submit(self: @R) -> i32\n"
            "        return sys_io_uring_enter(self.fd, 1, 0, 0)\n"
        ),
        [("status-return", "submit")],
    ),
    "status-return miss: -<digit> is sentinel-return's": (
        "pub fn find(s: StrView) -> i64\n    return -1\n",
        [("sentinel-return", "find")],
    ),
    "status-return miss: Result return": (
        "pub fn close_it(fd: i32) -> Result<i32, Errno>\n    return sys_close(fd)\n",
        [],
    ),
    "status-return miss: a sys_ prefix in a longer name, or no call": (
        (
            "pub fn a(fd: i32) -> i32\n    return my_sys_close(fd)\n"
            "pub fn b(fd: i32) -> i32\n    return sys_count\n"
        ),
        [],
    ),
    "status-return miss: private fn": (
        "fn close_it(fd: i32) -> i32\n    return syscall1(3, fd as i64) as i32\n",
        [],
    ),
    # S-RESULT-3 (#4636): a result written through a parameter.
    "out-param hit: :& StrView assigned": (
        (
            "struct S\n    n: i64\n\nimpl S\n"
            "    pub fn split_once(self: StrView, d: u8, before:& StrView, after:& StrView) -> i32\n"
            "        before.len = 0\n        after = self\n        1\n"
        ),
        [("out-param", "split_once"), ("out-param", "split_once")],
    ),
    "out-param hit: @&i32 written through *": (
        (
            "pub fn getname(fd: i32, ip: @&i32, port: @&i32) -> i32\n"
            "    *ip = 1\n    *port += 2\n    0\n"
        ),
        [("out-param", "getname"), ("out-param", "getname")],
    ),
    "out-param hit: *i32 handed to a syscall": (
        "pub fn pipe_it(pipefd: *i32) -> i32\n    return syscall1(22, pipefd as i64) as i32\n",
        [("out-param", "pipe_it"), ("raw-ptr-param", "pipe_it"), ("status-return", "pipe_it")],
    ),
    "out-param hit: *(p + k) = x and p[i] = x": (
        "pub fn fill(p: **u8, q: *i64)\n    *(p + 1) = null\n    q[0] = 3\n",
        [("out-param", "fill"), ("out-param", "fill"),
         ("raw-ptr-param", "fill"), ("raw-ptr-param", "fill")],
    ),
    "out-param miss: only read, or compared": (
        "pub fn peek(n:& i64, m: @&i32) -> i64\n    if *m == 3\n        return n\n    n + 1\n",
        [],
    ),
    "out-param miss: a struct written through @&": (
        "pub fn grow(v: @&Vec<u8>)\n    v.len = 0\n",
        [],
    ),
    "out-param miss: a byte buffer handed to a syscall": (
        "pub fn rd(fd: i32, buf: *u8) -> i64\n    let r = syscall3(0, fd as i64, buf as i64, 4)\n    r\n",
        [("raw-ptr-param", "rd")],
    ),
    "out-param miss: an argv array handed to a syscall": (
        (
            "pub fn exec(path: StrView, argv: **u8) -> i32\n"
            "    return syscall3(59, path.ptr as i64, argv as i64, 0) as i32\n"
        ),
        [("raw-ptr-param", "exec"), ("status-return", "exec")],
    ),
    "out-param miss: only another variable assigned": (
        "pub fn f(out: @&i32) -> i32\n    let x = out\n    var y = 0\n    y = 1\n    0\n",
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


def test_file_exemption_scoped_to_a_name_pattern():
    """#4636: `standard-exempt-file(sys_*)` covers the kernel-ABI fns only."""
    text = (
        "# sys.ritz\n"
        "# standard-exempt-file(sys_*): status-return: the kernel ABI returns raw -errno\n"
        "\n"
        "pub fn sys_close(fd: i32) -> i32\n    return syscall1(3, fd as i64) as i32\n"
        "pub fn close_fd(fd: i32) -> i32\n    return syscall1(3, fd as i64) as i32\n"
    )
    sites = {s.fn: s.exempt for s in scan_source(text, "lib/sys.ritz")}
    assert sites == {"sys_close": "the kernel ABI returns raw -errno", "close_fd": None}


def test_scoped_file_exemption_without_reason_is_malformed():
    text = "# standard-exempt-file(sys_*): status-return: abi\n\npub fn sys_x() -> i32\n    0\n"
    assert ("exempt-malformed", "sys_x") in keys(text)


# ---------------------------------------------------------------------------
# The tree walk, the summary and the CLI.
# ---------------------------------------------------------------------------


def test_tree_skips_test_directories(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.ritz").write_text("pub fn f(p: *u8)\n    pass\n")
    (tmp_path / "a.ritz").write_text("pub fn g(p: *u8)\n    pass\n")
    assert [s.fn for s in scan_tree([tmp_path])] == ["g"]


def _summary(**counts):
    out = summarise([])
    for key, (v, e) in counts.items():
        out[key.replace("_", "-")] = {"violations": v, "exempt": e}
    return out


def test_ratchet_passes_at_or_below_the_pin_and_on_a_new_exemption():
    pins = {"status-return": (3, 5)}
    assert ratchet_breaches(_summary(status_return=(3, 2)), pins) == []
    assert ratchet_breaches(_summary(status_return=(1, 2)), pins) == []  # migrated
    assert ratchet_breaches(_summary(status_return=(2, 3)), pins) == []  # exempted


def test_ratchet_fails_on_a_new_site_exempt_or_not():
    pins = {"status-return": (3, 5)}
    assert ratchet_breaches(_summary(status_return=(4, 2)), pins) == [
        "status-return: 4 violations > pin 3", "status-return: 6 sites (violations + exempt) > pin 5"]
    assert ratchet_breaches(_summary(status_return=(3, 3)), pins) == [
        "status-return: 6 sites (violations + exempt) > pin 5"]


def test_ratchet_pins_an_unnamed_key_at_zero():
    assert ratchet_breaches(_summary(out_param=(1, 0)), {}) == [
        "out-param: 1 violations > pin 0", "out-param: 1 sites (violations + exempt) > pin 0"]


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
# --callers (#4636): the exempt raw APIs, called from outside the library.
# ---------------------------------------------------------------------------

LIB_SYS = (
    "# standard-exempt: raw-ptr-param: close(2) kernel ABI for the test\n"
    "pub fn sys_pipe(p: *i32) -> i32\n    0\n"
    "pub fn sys_getpid() -> i32\n    0\n"
)
LIB_MEM = (
    "# standard-exempt-file: raw-alloc: this module is the allocator\n\n"
    "pub fn malloc(n: i64) -> *u8\n    sys_mmap(n)\n"
    "impl Pool\n    pub fn grab(self: @&Pool) -> *u8\n        malloc(1)\n"
)


def _tree(tmp_path, files):
    for rel, text in files.items():
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)


def test_exempt_apis_are_the_public_free_fns_with_an_exempt_site(tmp_path):
    _tree(tmp_path, {"lib/sys.ritz": LIB_SYS, "lib/memory.ritz": LIB_MEM})
    apis = exempt_apis(tmp_path / "lib")
    assert apis == {"sys_pipe": {"sys"}, "malloc": {"memory"}}


def test_callers_count_import_filtered_calls_outside_the_library(tmp_path):
    _tree(tmp_path, {
        "lib/sys.ritz": LIB_SYS,
        "lib/memory.ritz": LIB_MEM,
        # The library's own calls don't count.
        "lib/io.ritz": "import ritzlib.sys\nfn f()\n    sys_pipe(null)\n",
        "proj/a/main.ritz": (
            "import ritzlib.sys\nimport ritzlib.memory { malloc }\n"
            "fn main() -> i32\n"
            "    sys_pipe(null)\n"
            "    let p = malloc(4)  # malloc(5) in a comment\n"
            "    s.sys_pipe(null)\n"          # a method call, not the API
            "    sys_getpid()\n"             # not exempt
            "    0\n"
        ),
        # No import of ritzlib.sys: a local fn of the same name.
        "proj/b/x.ritz": "fn sys_pipe(p: *i32) -> i32\n    0\nfn g()\n    sys_pipe(null)\n",
        # Imports the module but not the name.
        "proj/b/y.ritz": "import ritzlib.memory { free }\nfn g()\n    malloc(1)\n",
        # Build output and caches are not the tree.
        "proj/b/build/gen.ritz": "import ritzlib.sys\nfn g()\n    sys_pipe(null)\n",
        "proj/b/.cache/gen.ritz": "import ritzlib.sys\nfn g()\n    sys_pipe(null)\n",
    })
    sites = count_callers(tmp_path / "lib", [tmp_path / "proj"])
    got = sorted((s.api, Path(s.path).relative_to(tmp_path).as_posix(), s.line) for s in sites)
    assert got == [("malloc", "proj/a/main.ritz", 5), ("sys_pipe", "proj/a/main.ritz", 4)]


def test_callers_totals_per_project(tmp_path):
    _tree(tmp_path, {
        "lib/sys.ritz": LIB_SYS,
        "proj/a/m.ritz": "import ritzlib.sys\nfn f()\n    sys_pipe(null)\n    sys_pipe(null)\n",
        "proj/b/src/m.ritz": "import ritzlib.sys\nfn f()\n    sys_pipe(null)\n",
    })
    sites = count_callers(tmp_path / "lib", [tmp_path / "proj"])
    assert callers_by_project(sites, tmp_path / "proj") == {"a": 2, "b": 1}


@pytest.mark.integration
def test_cli_callers(tmp_path):
    _tree(tmp_path, {
        "lib/sys.ritz": LIB_SYS,
        "proj/a/m.ritz": "import ritzlib.sys\nfn f()\n    sys_pipe(null)\n",
    })
    out = subprocess.run(
        [sys.executable, str(TOOL), "--callers", "--lib", str(tmp_path / "lib"),
         "--json", str(tmp_path / "proj")],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    assert data["by_api"] == {"sys_pipe": 1} and data["by_project"] == {"a": 1}


# ---------------------------------------------------------------------------
# The report itself is held to docs/STANDARD.md.  Per-module pins live in
# tools/test_standard_pins/, one file per module (AGAST #4551).
# ---------------------------------------------------------------------------


def test_every_counting_rule_names_a_rule_in_the_standard():
    """A key here points at a rule ID in docs/STANDARD.md, and the doc names the key."""
    doc = STANDARD.read_text()
    for key, (rule_id, _) in RULES.items():
        assert f"#### {rule_id} " in doc, f"{key}: {rule_id} is not a rule in STANDARD.md"
        assert f"`{key}`" in doc, f"{key} is not named in STANDARD.md"

