"""AGAST #3653: a fn-type field taking a struct by value came before that struct's `= type`.

    struct Info
        get: fn(name: StrView) -> StrView     # lexis's ElementInfo.get_attribute

ritz0 printed its identified types in the order it created them, so `Info`'s
body came first:

    %"struct.ritz_module_1.Info" = type {%"StrView" (%"StrView")*, i64}
    %"StrView" = type {i8*, i64}

and clang refused it: `error: invalid type for function argument`.  A named type
is forward-referenced (opaque) at that point. That is fine as a by-value struct
field or a pointee, but not as a function type's parameter or result.  The
builtin `StrView` is made lazily, the first time a type names it, so it always
came after the first struct that named it.  A user struct declared after its
use failed the same way.

ritz0 now orders the type definitions before printing: a struct whose body
holds a function type with a struct parameter or result by value comes after
that struct.  ritz1 and ritz1_selfhosted were already correct. Every row runs
all three, so they stay in agreement.
"""

import os
import subprocess

import pytest

import fast_link
from ritz0_inproc import run_ritz0

RITZ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RITZ1_BUILD = os.path.join(RITZ_ROOT, "ritz1", "build")
RITZ_START = os.path.join(RITZ_ROOT, "runtime", "ritz_start.x86_64.o")

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

SHAPES = """\
pub struct S
    a: i64
    b: i64
"""

S_LATER = """\
struct S
    a: i64
    b: i64
"""

USE_S = """\
fn ident(s: S) -> S
    s

fn make() -> S
    S { a: 4, b: 5 }

fn main() -> i32
    let i = Info { f: ident, n: 3 }
    let r = (i.f)(S { a: 4, b: 5 })
    if r.a + r.b != 9
        return 1
    return 42
"""

# name -> (main.ritz, {other module: source})
CASES = {
    # The ticket: lexis's `get_attribute: fn(name: StrView) -> StrView`.
    "builtin_strview": ("""\
struct Info
    get: fn(name: StrView) -> StrView
    n: i64

fn first(s: StrView) -> StrView
    s

fn main() -> i32
    let i = Info { get: first, n: 3 }
    let r = (i.get)("hey")
    if r.len != 3
        return 1
    return 42
""", {}),
    # A user struct declared after the struct whose fn field takes it.
    "declared_later": ("struct Info\n    f: fn(s: S) -> S\n    n: i64\n\n" + S_LATER + "\n" + USE_S, {}),
    # Only the result is the later struct.
    "result_only": ("""\
struct Info
    f: fn() -> S
    n: i64

""" + S_LATER + """
fn make() -> S
    S { a: 4, b: 5 }

fn main() -> i32
    let i = Info { f: make, n: 3 }
    let r = (i.f)()
    if r.a + r.b != 9
        return 1
    return 42
""", {}),
    # The struct comes from an import.
    "imported": ("import shapes\n\nstruct Info\n    f: fn(s: S) -> S\n    n: i64\n\n" + USE_S,
                 {"shapes": SHAPES}),
    # The fn type sits inside an array field, and the struct holding it is itself
    # a by-value field of a struct declared first.
    "nested": ("""\
struct Outer
    inner: Info
    k: i64

struct Info
    fs: [2]fn(s: S) -> S
    n: i64

""" + S_LATER + """
fn ident(s: S) -> S
    s

fn swap(s: S) -> S
    S { a: s.b, b: s.a }

fn main() -> i32
    let o = Outer { inner: Info { fs: [ident, swap], n: 3 }, k: 1 }
    # Through typed locals: ritz1 loses the fn type of `(o.inner.fs[1])(..)`
    # and of an untyped `let` holding its result (#3666).
    let h: fn(s: S) -> S = o.inner.fs[1]
    let r: S = h(S { a: 4, b: 5 })
    if r.a != 5 or r.b != 4
        return 1
    return 42
""", {}),
    # A's fn returns B, and B's fn takes A by value. Only the parameter is an
    # ordering edge, so A stays first. If the result counted too, the cycle
    # would put B first and leave its parameter A forward-referenced.
    "result_cycle": ("""\
struct A
    f: fn() -> B
    n: i64

struct B
    g: fn(a: A) -> i64
    m: i64

fn mk() -> B
    B { g: an, m: 5 }

fn an(a: A) -> i64
    a.n

fn main() -> i32
    let a = A { f: mk, n: 7 }
    let b: B = (a.f)()
    if (b.g)(a) + b.m != 12
        return 1
    return 42
""", {}),
    # A pointer cycle through fn types (A's fn takes B, B's fn takes *A) still orders.
    "pointer_cycle": ("""\
struct A
    f: fn(b: B) -> i64
    n: i64

struct B
    g: fn(a: *A) -> i64
    m: i64

fn fb(b: B) -> i64
    b.m

fn ga(a: *A) -> i64
    a.n

fn main() -> i32
    var a = A { f: fb, n: 7 }
    let b = B { g: ga, m: 5 }
    if (a.f)(b) + (b.g)(@a) != 12
        return 1
    return 42
""", {}),
}


def _run(compiler, tmp_path, name):
    main, others = CASES[name]
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    (work / "main.ritz").write_text(main)
    for mod, text in others.items():
        (work / f"{mod}.ritz").write_text(text)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{work}")
    if compiler == "ritz0":
        comp = run_ritz0([str(work / "main.ritz"), "-o", str(ll)], cwd=work, env=env, timeout=300)
    else:
        binary = os.path.join(RITZ1_BUILD, compiler)
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert os.path.exists(binary), f"{binary} missing; run `make -C ritz1 bootstrap`"
        comp = subprocess.run([binary, str(work / "main.ritz"), "-o", str(ll)], check=False, cwd=work,
                              env=env, capture_output=True, text=True, timeout=300)
    assert comp.returncode == 0 and ll.exists(), \
        f"{compiler} refused {name}:\n{comp.stdout}{comp.stderr}"[-2000:]
    exe = work / "main"
    cmd = ["clang", "-Wno-override-module", "-O2", str(ll), "-o", str(exe), "-nostdlib", "-no-pie"]
    if compiler != "ritz0":
        cmd.insert(1, RITZ_START)
    link = fast_link.clang(cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: clang refused {name}:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], check=False, capture_output=True, timeout=60).returncode


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_fn_type_field_runs(compiler, name, tmp_path):
    assert _run(compiler, tmp_path, name) == 42
