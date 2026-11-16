"""AGAST #1685: ritz1 hoists every fixed-size alloca into the entry block.

THE DEFECT

ritz1 emitted `alloca` at the point a local or temp first appeared.  Inside a
loop body that is a fresh stack slot per iteration, and the stack is never
reclaimed until the function returns -- LLVM does not hoist non-entry allocas
(they are dynamic allocas by definition).  A 10M-iteration loop with a
16-byte `let q: P = ..` in its body therefore needs 160 MB of stack and
segfaults; ritz0, which hoists, exits normally.

Every in-place temp had the same shape: the local itself, the rvalue
struct-literal temp (#1362), the method-receiver literal slot, the
variant-ctor slot, the newtype arg box (gone since LARB R47b, #3420: its
argument is refused) and emit_array_fill_into's counter.

THE FIX

emit_fn / emit_impl_method remember where the body starts (just after
`entry:`) and, once the body is emitted, move every fixed-size
`%r = alloca <type>` line up to that point (hoist_entry_allocas).  A
`__builtin_alloca(n)` stays where it is: its size is a runtime value and its
per-call semantics are the point.

THE TESTS

  * structural: for each temp kind inside a loop, every fixed-size alloca
    in every function of ritz1's IR is in the entry block.
  * runtime: the same programs run 10M iterations under an 8 MB stack and
    exit with ritz0's code (the ticket's repro segfaulted).  ritz0 itself
    still grows the stack for two temps (#1734); those oracles are xfail.
  * dynamic: `__builtin_alloca(n)` is NOT hoisted (its operand is defined
    later than `entry:`; hoisting it would be invalid IR).
"""

import os
import re
import resource
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0
from test_ritz1_builtin_struct_shadow import RITZ1_BIN, RITZ_ROOT, RITZ_START

ITERS = 10_000_000

# --- one program per alloca site, each inside a hot loop ---------------------

# The ticket's repro verbatim: a struct-typed `let` in the loop body.
LET_LOCAL = f"""\
struct P
    x: i64
    y: i64

fn sum(p: P) -> i64
    return p.x + p.y

pub fn main() -> i32
    var t: i64 = 0
    var i: i64 = 0
    while i < {ITERS}
        let q: P = P {{ x: 1, y: 0 }}
        t = t + sum(q)
        i = i + 1
    return (t / 1000000) as i32
"""

# The rvalue struct-literal temp (#1362): a literal straight into a call.
RVALUE_LIT = f"""\
struct P
    x: i64
    y: i64

fn sum(p: P) -> i64
    return p.x + p.y

pub fn main() -> i32
    var t: i64 = 0
    var i: i64 = 0
    while i < {ITERS}
        t = t + sum(P {{ x: 1, y: 1 }})
        i = i + 1
    return (t / 1000000) as i32
"""

# A struct literal as a method argument inside an impl method's loop
# (exercises emit_impl_method as well as emit_fn).
METHOD_LOOP = f"""\
struct P
    x: i64
    y: i64

struct Acc
    base: i64

impl Acc
    fn add(self: @Acc, p: P) -> i64
        return self.base + p.x + p.y

    fn run(self: @Acc) -> i64
        var t: i64 = 0
        var i: i64 = 0
        while i < {ITERS}
            t = t + self.add(P {{ x: 1, y: 1 }})
            i = i + 1
        return t

pub fn main() -> i32
    let a: Acc = Acc {{ base: 1 }}
    return (a.run() / 1000000) as i32
"""

# The variant-ctor slot: `Some(..)` built every iteration.
VARIANT_CTOR = f"""\
fn take(o: Option<i64>) -> i64
    return match o
        Some(v) => v
        None => 0

pub fn main() -> i32
    var t: i64 = 0
    var i: i64 = 0
    while i < {ITERS}
        t = t + take(Some(4))
        i = i + 1
    return (t / 1000000) as i32
"""

# emit_array_fill_into's counter: a `[v; N]` field fill with N > 16 is a
# real counted loop whose counter is an alloca.
ARRAY_FILL = f"""\
struct Q
    a: [20]i64
    n: i64

pub fn main() -> i32
    var t: i64 = 0
    var i: i64 = 0
    while i < {ITERS // 10}
        let q: Q = Q {{ a: [5; 20], n: 0 }}
        t = t + q.a[19] + q.n
        i = i + 1
    return (t / 100000) as i32
"""

CASES = {
    "let_local": (LET_LOCAL, 10),
    "rvalue_lit": (RVALUE_LIT, 20),
    "method_loop": (METHOD_LOOP, 30),
    "variant_ctor": (VARIANT_CTOR, 40),
    "array_fill": (ARRAY_FILL, 50),
}

# The struct-literal method receiver is lowered in ritz1 only (ritz0 rejects
# the form), so it gets the structural check but no ritz0 oracle.  The newtype
# arg box's case (`a.add(i * 1)`) went with the box: since LARB R47b (#3420) its
# argument is refused, test_nonstruct_arg_for_struct_param.py.
RECV_LIT = """\
struct P
    x: i64
    y: i64

impl P
    fn total(self: @P) -> i64
        return self.x + self.y

pub fn main() -> i32
    var t: i64 = 0
    var i: i64 = 0
    while i < 10
        t = t + P { x: 1, y: 2 }.total()
        i = i + 1
    return t as i32
"""

STRUCTURAL_CASES = {name: prog for name, (prog, _) in CASES.items()}
STRUCTURAL_CASES["recv_lit"] = RECV_LIT

# A runtime-sized __builtin_alloca must stay put.
DYNAMIC_ALLOCA = """\
fn fill(n: i64) -> i64
    var t: i64 = 0
    var i: i64 = 0
    while i < 3
        let p: *u8 = __builtin_alloca(n + i) as *u8
        *p = 7
        t = t + (*p as i64)
        i = i + 1
    return t

pub fn main() -> i32
    return fill(8) as i32
"""

# --- helpers -----------------------------------------------------------------

STACK_BYTES = 8 * 1024 * 1024
AS_BYTES = 2 * 1024 * 1024 * 1024


def _limits() -> None:
    """A fixed 8 MB stack makes the old per-iteration growth a deterministic
    segfault; the address-space cap keeps a runaway off the host."""
    resource.setrlimit(resource.RLIMIT_STACK, (STACK_BYTES, STACK_BYTES))
    resource.setrlimit(resource.RLIMIT_AS, (AS_BYTES, AS_BYTES))


def _compile(compiler: str, tmp_path: Path, name: str, program: str) -> Path:
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
        comp = subprocess.run(
            cmd,
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return ll


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    ll = _compile(compiler, tmp_path, name, program)
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run(
        [str(exe)], capture_output=True, timeout=120, preexec_fn=_limits
    ).returncode


# ritz1 ends the `define` line with `{`; ritz0 puts `{` on the next line.
_DEFINE = re.compile(r"^define\b")
_LABEL = re.compile(r"^[A-Za-z_.$][\w.$]*:")
# ritz0 quotes register names (`%"q.addr"`); ritz1 does not.
_ALLOCA = re.compile(r'^\s*%"?[\w.$]+"? = alloca (.*)$')


def _misplaced_allocas(ll_text: str) -> list:
    """Return `(fn header, line)` for every fixed-size alloca that is NOT in
    its function's entry block.  An alloca with a register operand
    (`alloca i8, i64 %.5`) is dynamic and exempt."""
    bad = []
    header = None
    in_entry = False
    for line in ll_text.splitlines():
        if _DEFINE.match(line):
            header = line
            in_entry = False
            continue
        if header is None:
            continue
        if line.startswith("}"):
            header = None
            continue
        if _LABEL.match(line):
            in_entry = line.startswith("entry:")
            continue
        m = _ALLOCA.match(line)
        if m and not in_entry:
            operand = m.group(1).split(";")[0]
            if "%." not in operand:
                bad.append((header, line.strip()))
    return bad


# --- tests -------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(STRUCTURAL_CASES))
def test_ritz1_allocas_in_entry_block(ritz1_bin, tmp_path, name):
    """Every fixed-size alloca lives in `entry:`, never in a loop block."""
    ll = _compile("ritz1", tmp_path, name, STRUCTURAL_CASES[name])
    text = ll.read_text()
    # Guard against a vacuous pass: the program must have a loop block.
    assert re.search(r"^L\d+:", text, re.M), f"{name}: no loop block emitted"
    bad = _misplaced_allocas(text)
    assert not bad, f"{name}: allocas outside the entry block:\n" + "\n".join(
        f"  {h}\n    {line}" for h, line in bad
    )


# The twins of the two #1734 sites, ritz0 only.  A call argument or an
# annotated `let` builds its variant through the expected-enum constructor; an
# unannotated `let` has no expected enum and takes the bare constructor.  `@v`
# of a match payload takes its address through the `@` path rather than the
# place path.
VARIANT_UNTYPED = f"""\
enum E
    A(i64)
    B

fn get(e: E) -> i64
    return match e
        A(v) => v
        B => 0

pub fn main() -> i32
    var t: i64 = 0
    var i: i64 = 0
    while i < {ITERS}
        let e = A(4)
        t = t + get(e)
        i = i + 1
    return (t / 1000000) as i32
"""

VARIANT_TYPED = f"""\
fn take(o: Option<i64>) -> i64
    return match o
        Some(v) => v
        None => 0

pub fn main() -> i32
    var t: i64 = 0
    var i: i64 = 0
    while i < {ITERS}
        let o: Option<i64> = Some(4)
        t = t + take(o)
        i = i + 1
    return (t / 1000000) as i32
"""

# The loop is inside the arm, so only `v.addr` is in it (the scrutinee's
# own `match.enum` slot is a separate site, kept out of this case).
ADDR_OF_PAYLOAD = f"""\
fn rd(p: @i64) -> i64
    return *p

pub fn main() -> i32
    var t: i64 = 0
    var i: i64 = 0
    match Some(2)
        Some(v) =>
            while i < {ITERS}
                t = t + rd(@v)
                i = i + 1
        None => t = 0
    return (t / 1000000) as i32
"""

RITZ0_CASES = dict(
    CASES,
    variant_untyped=(VARIANT_UNTYPED, 40),
    variant_typed=(VARIANT_TYPED, 40),
    addr_of_payload=(ADDR_OF_PAYLOAD, 20),
)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ0_CASES))
def test_ritz0_allocas_in_entry_block(tmp_path, name):
    """AGAST #1734: every fixed-size alloca ritz0 emits is in `entry:`."""
    ll = _compile("ritz0", tmp_path, name, RITZ0_CASES[name][0])
    text = ll.read_text()
    assert re.search(r"^while\.body:", text, re.MULTILINE), (
        f"{name}: no loop block emitted"
    )
    bad = _misplaced_allocas(text)
    assert not bad, f"{name}: allocas outside the entry block:\n" + "\n".join(
        f"  {h}\n    {line}" for h, line in bad
    )


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ0_CASES))
def test_ritz0_oracle(tmp_path, name):
    """The reference answer, under the same 8 MB stack. If this changes, the
    oracle moved, not ritz1."""
    program, want = RITZ0_CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_long_loop_does_not_grow_stack(ritz1_bin, tmp_path, name):
    """10M iterations under an 8 MB stack: exits with ritz0's code."""
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
def test_ritz1_dynamic_alloca_stays_in_place(ritz1_bin, tmp_path):
    """`__builtin_alloca(n)` has a runtime size: it is not hoisted."""
    ll = _compile("ritz1", tmp_path, "dyn", DYNAMIC_ALLOCA)
    text = ll.read_text()
    fn = text[text.index("define") :]
    fn = fn[fn.index("@fill") :]
    body = fn[: fn.index("\n}")]
    entry = body.split("\nL", 1)[0]
    assert re.search(r"alloca i8, i64 %\.", body), "dynamic alloca missing"
    assert not re.search(r"alloca i8, i64 %\.", entry), (
        "dynamic alloca was hoisted into entry:\n" + entry
    )
    exe_rc = _run("ritz1", tmp_path, "dyn", DYNAMIC_ALLOCA)
    assert exe_rc == 21
