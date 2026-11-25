"""AGAST #4689: ritzlib's raw `*T` return types, pinned down-only.

STANDARD.md S-PTR-7: a return value is a value, a borrow or a view, not a raw
`*T`.  `standard_report.py` counts each API fn whose return type is, or wraps,
a raw pointer as `ptr-return`.  The base had 49 outside tests; #4689 ported
`HashMap.get_ptr` / `HashMapI64.value_ptr` -> `get_mut -> Option<@&V>`,
`ElfReader.get_symbol_name -> Option<StrView>`, the async task/runtime returns
(`task_server_create`, `TaskPool.alloc/find`, `get_runtime`) and the uring
`get_sqe` / `peek_cqe` / `wait_cqe` to borrows (`@&IoUringSqe`, `@IoUringCqe`),
and exempted the genuine raw outputs with a reason: the allocators
(memory), mmap (sys), libc-shaped str, and the `as_ptr` / `get_ptr` accessors
and iovec array that exist to hand C a pointer.

json.ritz's five went with AGAST #4690 (enum Json, borrows `Option<@Json>`); left as a
violation: `Vec.as_str` (#4688).

A module not listed is pinned at zero, so a new `pub fn f() -> Option<*T>`
anywhere in ritzlib fails here.  The pin is a ceiling of (violations,
violations + exempt), like the other C-shape pins.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree

pytestmark = pytest.mark.unit

RITZLIB = Path(__file__).resolve().parent.parent.parent / "ritzlib"

# module (path under ritzlib) -> (violations, violations + exempt)
PINS: dict[str, tuple[int, int]] = {
    "box.ritz": (0, 1),
    "gvec.ritz": (1, 3),     # as_str is #4688's
    "iovec.ritz": (0, 1),
    "memory.ritz": (0, 11),
    "span.ritz": (0, 2),
    "str.ritz": (0, 7),
    "string.ritz": (0, 1),
    "strview.ritz": (0, 2),
    "sys.ritz": (0, 5),
}

# Ported to borrows or views: no raw return may come back in these.
PORTED = ("hashmap.ritz", "elf.ritz", "uring.ritz", "async/tasks.ritz", "async/runtime.ritz",
          "async_net.ritz", "mapping.ritz", "json.ritz")


def ptr_returns(root: Path) -> dict[str, tuple[int, int]]:
    """{module: (violations, violations + exempt)} of ptr-return under `root`."""
    out: dict[str, list[int]] = {}
    for s in scan_tree([root]):
        if s.key == "ptr-return":
            c = out.setdefault(Path(s.path).relative_to(root).as_posix(), [0, 0])
            c[0] += s.exempt is None
            c[1] += 1
    return {k: (v, t) for k, (v, t) in out.items()}


def test_ptr_returns_only_go_down():
    breaches = [
        f"{mod}: {got} raw returns (violations, total) > pin {PINS.get(mod, (0, 0))}"
        for mod, got in sorted(ptr_returns(RITZLIB).items())
        if got[0] > PINS.get(mod, (0, 0))[0] or got[1] > PINS.get(mod, (0, 0))[1]
    ]
    assert breaches == []


def test_ported_modules_return_no_raw_pointer():
    got = ptr_returns(RITZLIB)
    assert {m: got[m] for m in PORTED if m in got} == {}


def test_a_new_raw_return_turns_the_pin_red(tmp_path):
    """Mutation check: `-> Option<*T>` and `-> *T` in an unpinned module count."""
    (tmp_path / "foo.ritz").write_text(
        "struct Foo\n    n: i64\n\nimpl Foo\n    pub fn find(self: @Foo) -> Option<*i64>\n        None\n\n"
        "# standard-exempt: ptr-return: the raw accessor for interop\n"
        "pub fn raw() -> *u8\n    0 as *u8\n")
    assert ptr_returns(tmp_path) == {"foo.ritz": (1, 2)}


def test_munmap_is_the_one_raw_alloc_site_made_exempt():
    """The raw-alloc count is 0 violations in ritzlib: mapping.munmap is exempt, not open."""
    mapping = [s for s in scan_tree([RITZLIB / "mapping.ritz"]) if s.key == "raw-alloc"]
    assert [(s.fn, s.exempt is not None) for s in mapping] == [("munmap", True)]
