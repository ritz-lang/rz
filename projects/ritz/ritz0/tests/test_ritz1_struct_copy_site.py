"""AGAST #4461: the sret copy choice is made where the copy is emitted.

THE DEFECT

#1732 fixed the first-class large-struct copy by re-parsing the finished
function body: rewrite_large_struct_copies copied the body out of `s.out`,
scanned it line by line looking for a `store %T %.V` whose defining line was
`%.V = load %T, ptr SRC` with nothing in between that could write memory, and
replaced it with a call to `@__ritz_sret_copy`.  drop_dead_large_loads then
dropped every large `load %T` its register was not read from -- including the
one the emitter writes after every sret call, which -O2 expands per leaf and
which #3952 measured blowing up clang on a 64 KB payload.

The scanning helpers lived in a second module, ll_copy_scan.ritz, purely so a
unit test could drive them with hand-written IR.

THE FIX

The emitter knows both facts at the point it emits them: a whole-struct load
of an sret-sized type is *deferred* -- its register is burned and its line is
held in EmitterState -- and a struct store consumes the record when nothing
emitted since the load could write memory (the old pass's line test, applied
to the emitted range rather than to a re-parsed body):

    record:  %.5 = load %Big, ptr %.4     (held, not written)
             ... getelementptr ...        (cannot write, tolerated)
    store:   store %Big %.5, ptr %.2      (replaced:)
             call void @__ritz_sret_copy(ptr %.2, ptr %.4, i64 sizeof(%Big))

Anything that can write memory in between (a drop, a call, a branch, a store)
leaves the record to be written back: the old pass refused the rewrite then
too, and the load reappears at its original offset when the function body is
complete.  A record still held there is dropped when its register was never
referenced (`used`), as drop_dead_large_loads did; a register read somewhere
else keeps its load even when a store also consumed it.  Register numbering
is unchanged: next_reg is called at every former load site, so the register
gaps the old pass left are still there.

Nothing scans emitted IR text for copies any more, and ll_copy_scan.ritz is
deleted.  The generic line scanners the (still present, #4462) packed-align
pass uses, and the range check above, live in emitter_core.ritz under
non-`ll_` names, so the acceptance grep

    git grep -n "ll_starts_with\\|ll_line_len" projects/ritz/ritz1/src

finds nothing.

THE TESTS

  * source shape: the passes and the module are gone, and no `ll_starts_with`
    / `ll_line_len` caller survives.
  * structural: for each copy form the corpus exercises (local copy, deref,
    assignment, sret-call result, by-value argument spill, struct-field
    store, inline and pointer field-array element store, member read),
    ritz1's IR has the helper call and no first-class `store %Big`; a
    discarded sret result has no `load %Big` at all.
"""

import re
import subprocess
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import RITZ1_BIN, RITZ_ROOT

SRC = RITZ_ROOT / "ritz1" / "src"
DELETED_MODULE = SRC / "ll_copy_scan.ritz"

# Names the deleted implementation carried.  A comment naming one is stale
# documentation; the ticket deletes them all.
DELETED_SYMBOLS = (
    "rewrite_large_struct_copies",
    "drop_dead_large_loads",
    "dead_large_load_reg",
    "try_emit_large_copy",
    "ll_find_copy",
    "LlCopy",
    "ll_copy_scan",
)

# The acceptance grep: these two names were ll_copy_scan's (and the deleted
# pass's).  The generic scanners the packed-align pass still needs were moved
# and renamed, so nothing in ritz1/src is called by either name.
SCAN_SYMBOLS = ("ll_starts_with", "ll_line_len")


def _sources() -> dict:
    return {p.name: p.read_text() for p in sorted(SRC.glob("*.ritz"))}


# --- source shape ------------------------------------------------------------


@pytest.mark.unit
def test_copy_pass_and_its_scanner_module_are_deleted():
    assert not DELETED_MODULE.exists(), (
        "ll_copy_scan.ritz still exists; the copy decision is made at the "
        "emission site (#4461)")
    found = []
    for name, text in _sources().items():
        for sym in DELETED_SYMBOLS:
            if sym in text:
                found.append(f"{name}: {sym}")
    assert not found, (
        "deleted copy-pass names survive (#4461):\n" + "\n".join(found))


@pytest.mark.unit
def test_no_copy_scanner_callers_survive():
    found = []
    for name, text in _sources().items():
        for sym in SCAN_SYMBOLS:
            for i, line in enumerate(text.splitlines(), 1):
                if sym in line:
                    found.append(f"{name}:{i}: {line.strip()}")
    assert not found, (
        "ll_copy_scan scanners still have callers (#4461):\n"
        + "\n".join(found))


# --- structural: the copy choice appears at the emission site ---------------

DECLS = """\
struct Big
    buf: [512]u8
    n: i32

struct Holder
    b: Big
    bs: [4]Big
    pb: *Big

extern fn big_load(p: *Big)
extern fn big_sink(p: *Big) -> i32
"""

CASES = {
    # `var x: Big = *p`: the deref load feeds the local's store.
    "var_deref": """
pub fn f(p: *Big) -> i32
    var x: Big = *p
    return x.n
""",
    # `x = y`: the ident load feeds the assignment store.
    "assign_ident": """
pub fn f(p: *Big, q: *Big) -> i32
    var x: Big = *p
    x = *q
    return x.n
""",
    # `*d = *p`: destination evaluated first, then the source copy.
    "store_deref": """
pub fn f(p: *Big, d: *Big) -> i32
    *d = *p
    return 0
""",
    # `var x: Big = f()`: the sret slot is copied, never loaded + stored.
    "sret_result": """
fn make(n: i32) -> Big
    var b: Big = Big { buf: [0; 512], n: n }
    return b

pub fn f(n: i32) -> i32
    var x: Big = make(n)
    return x.n
""",
    # A discarded sret result must not leave its dead `load %Big` behind.
    "sret_discarded": """
fn make(n: i32) -> Big
    var b: Big = Big { buf: [0; 512], n: n }
    return b

pub fn f(n: i32) -> i32
    make(n)
    return n
""",
    # A large struct passed by value is spilled with a pointer copy
    # (#1739), not the first-class load/store pair.
    "byval_arg": """
fn take(v: Big) -> i32
    return v.n

pub fn f(p: *Big) -> i32
    return take(*p)
""",
    # `s.b = *p`: a struct field store.  The old pass rewrote it because the
    # load was the line immediately before; a GEP emitted in between must not
    # hide the pair.
    "field_store": """
pub fn f(p: *Big, s: *Holder) -> i32
    s.b = *p
    return s.b.n
""",
    # `h.bs[i] = *p`: an inline struct-array field element store.  It emits a
    # GEP between the load and the store, which the emission-time check has to
    # tolerate exactly as the line-based pass did.
    "field_array_elem_store": """
pub fn f(p: *Big, h: *Holder, i: i32) -> i32
    h.bs[i] = *p
    return h.bs[i].n
""",
    # `h.pb[i] = *p`: a pointer-field element store, same GEP in between.
    "ptr_field_elem_store": """
pub fn f(p: *Big, h: *Holder, i: i32) -> i32
    h.pb[i] = *p
    return h.pb[i].n
""",
    # `var x: Big = s.b`: a whole-struct member read is a deferred load too.
    "member_load": """
pub fn f(p: *Big, s: *Holder) -> i32
    var x: Big = s.b
    return x.n
""",
}

STORE_BIG = re.compile(r'^\s*store\s+%"?[\w.$]*Big"?\s+%')
LOAD_BIG = re.compile(r'^\s*%?[\w.$]+"?\s*=\s*load\s+%"?[\w.$]*Big"?\s*,')
COPY_CALL = re.compile(r'call void @"?__ritz_sret_copy"?\(')


def _compile_ritz1(tmp_path: Path, name: str, program: str) -> str:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}.ll"
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env={"RITZ_PATH": str(RITZ_ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 failed to compile {name}:\n{comp.stdout[-2000:]}\n"
        f"{comp.stderr[-2000:]}")
    return ll.read_text()


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_large_copy_is_a_pointer_copy_at_the_site(ritz1_bin, tmp_path, name):
    text = _compile_ritz1(tmp_path, name, DECLS + CASES[name])
    stores = [ln.strip() for ln in text.splitlines() if STORE_BIG.search(ln)]
    assert not stores, f"{name}: first-class large-struct stores survive: {stores}"
    if name in ("sret_discarded",):
        loads = [ln.strip() for ln in text.splitlines() if LOAD_BIG.search(ln)]
        assert not loads, (
            f"{name}: a dead `load %Big` after an sret call survives: {loads}")
    else:
        assert COPY_CALL.search(text), (
            f"{name}: no @__ritz_sret_copy call was emitted")
