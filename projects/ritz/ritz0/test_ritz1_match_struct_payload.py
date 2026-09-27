"""AGAST #1515: ritz1 binds a match arm's struct payload at its real type.

THE DEFECT

emit_match_arm_body (ritz1/src/emitter_match.ritz) bound every variant
payload (`Ok(s) =>`, `Some(p) =>`) as `alloca i64` / TYPE_I64, whatever the
variant carried. Over a `Result<String, i32>` or an `Option<Point>`:

  * handing the binding to a fn taking the struct gave clang
    "'%.N' defined with type 'i64' but expected '%Point'";
  * a field access on it (`p.x`) failed with "unhandled EXPR_MEMBER".

This blocked examples/tier5_async/69_result_string (and, with #1362,
76_option).

THE FIX

The carrier variant's (Ok/Some) payload type is the enum's mangled suffix
(`Option$Point` -> `Point`, `Result$String` -> `String`; ritz1 keeps only the
first type argument). When that names a known struct, the arm binding is an
`alloca %Point` holding a copy of the payload, registered as a struct local.
Scalar payloads and the Err/None side keep the i64 path.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run, _run_pkg, ritz1_bin  # noqa: F401

# Ticket repro 2a: field access on the bound struct.
OPTION_MEMBER = """\
struct Point
    x: i64
    y: i64

fn main() -> i32
    let p0: Point = Point { x: 3, y: 4 }
    var o: Option<Point> = Some(p0)
    let x: i64 = match o
        Some(p) => p.x
        None => 0
    return (x - 3) as i32
"""

# Ticket repro 2b: the bound struct passed by value to a fn.
OPTION_TO_FN = """\
struct Point
    x: i64
    y: i64

fn sum(p: Point) -> i64
    return p.x + p.y * 10

fn main() -> i32
    let p0: Point = Point { x: 3, y: 4 }
    var o: Option<Point> = Some(p0)
    let x: i64 = match o
        Some(p) => sum(p)
        None => 0
    return x as i32
"""

# Every field, not just the first: a wrong payload offset or a truncated
# (i64-sized) copy gets `y`/`z` wrong. Also the None arm on the same type.
OPTION_ALL_FIELDS = """\
struct Trio
    x: i64
    y: i64
    z: i64

fn pick(o: Option<Trio>) -> i64
    let r: i64 = match o
        Some(t) => t.x + t.y * 10 + t.z * 100
        None => 7
    return r

pub fn main() -> i32
    let t0: Trio = Trio { x: 1, y: 2, z: 3 }
    let s0: Option<Trio> = Some(t0)
    let n0: Option<Trio> = None
    let a: i64 = pick(s0)
    let b: i64 = pick(n0)
    if a != 321
        return 1
    if b != 7
        return 2
    return 42
"""

# Scalar payloads keep working (the i64 path is untouched).
SCALAR_PAYLOAD = """\
fn pick(o: Option<i32>) -> i32
    let r: i64 = match o
        Some(v) => v as i64 + 1
        None => 0
    return r as i32

pub fn main() -> i32
    let s0: Option<i32> = Some(41)
    let n0: Option<i32> = None
    let a: i32 = pick(s0)
    let b: i32 = pick(n0)
    if b != 0
        return 1
    return a
"""

# Ticket repro 1: Result<String, i32>; the Err side stays scalar.
RESULT_STRING = """\
import ritzlib.string
import ritzlib.result

fn take(s: String) -> i32
    return string_len(@s) as i32 + 3

pub fn main() -> i32
    let r: Result<String, i32> = Ok(string_new())
    match r
        Ok(s) => take(s)
        Err(e) => e
"""

RESULT_STRING_ERR = """\
import ritzlib.string
import ritzlib.result

fn take(s: String) -> i32
    return string_len(@s) as i32 + 3

fn mk() -> Result<String, i32>
    return Err(9)

pub fn main() -> i32
    let r: Result<String, i32> = mk()
    match r
        Ok(s) => take(s)
        Err(e) => e
"""

CASES = {
    "option_member": (OPTION_MEMBER, 0),
    "option_to_fn": (OPTION_TO_FN, 43),
    "option_all_fields": (OPTION_ALL_FIELDS, 42),
    "scalar_payload": (SCALAR_PAYLOAD, 42),
}

PKG_CASES = {
    "result_string": (RESULT_STRING, 3),
    "result_string_err": (RESULT_STRING_ERR, 9),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_match_struct_payload(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz0_oracle_pkg(tmp_path, name):
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz1_match_struct_payload_pkg(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want
