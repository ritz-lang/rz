"""Regression tests for AGAST #1813: ritz1 must never silently drop data at a
fixed capacity or an unhandled kind.

ritz1 had fixed-size tables (32 enums, 16 call args, 256 locals, 512 emitted
names, 64 match arms, 256 monomorph instantiations, 128/256-byte name buffers)
that dropped entries silently when full, so it miscompiled and exited 0. A tab
in indentation made the lexer loop forever.

Each table is now either growable, so the program compiles correctly with
ritz0 as the oracle (MUST_WORK), or a located fatal error that names the
limit (MUST_FAIL_LOUD). The ticket's acceptance cases (17 args, 33 enums) are
in MUST_WORK.
"""

import os
import subprocess
import time
from pathlib import Path

import pytest
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ1_SRC = RITZ_ROOT / "ritz1" / "src"
# Build product, not a tracked file; see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _compile(compiler: str, tmp_path: Path, name: str, program: str, timeout=300):
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        proc = run_ritz0([src, "-o", ll], cwd=tmp_path, env=env, timeout=timeout)
    else:
        proc = subprocess.run(
            [str(RITZ1_BIN), str(src), "-o", str(ll)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    return proc, ll


def _link_run(compiler: str, tmp_path: Path, name: str, ll: Path) -> int:
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({name}):\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return _link_run(compiler, tmp_path, name, ll)


def _fails_loud(tmp_path: Path, name: str, program: str, diagnostic: str):
    """ritz1 refuses with one located error naming the limit, and writes no
    output."""
    comp, ll = _compile("ritz1", tmp_path, name, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"ritz1 accepted {name} past its limit:\n{out[-2000:]}"
    assert f"{name}.ritz:" in out, f"diagnostic is not located:\n{out[-2000:]}"
    assert diagnostic in out, f"missing {diagnostic!r}:\n{out[-2000:]}"
    assert not ll.exists(), "ritz1 must not write output after an error"


# --- programs ---------------------------------------------------------------


def _many_args(n: int) -> str:
    params = ", ".join(f"a{i}: i64" for i in range(1, n + 1))
    args = ", ".join(str(i) for i in range(1, n + 1))
    return f"fn f({params}) -> i64\n    return a{n}\n\npub fn main() -> i32\n    return f({args}) as i32\n"


def _many_args_method(n: int) -> str:
    params = ", ".join(f"a{i}: i64" for i in range(1, n + 1))
    args = ", ".join(str(i) for i in range(1, n + 1))
    return (
        "struct S\n    k: i64\n\n"
        f"impl S\n    fn get(self: *S, {params}) -> i64\n        return a{n} + self.k\n\n"
        f"pub fn main() -> i32\n    var s: S = S {{ k: 1 }}\n    return s.get({args}) as i32\n"
    )


def _many_enums(n: int) -> str:
    """n enums E0..E(n-1); main matches on the LAST one's second variant."""
    parts = [f"enum E{i}\n    A{i}\n    B{i}\n" for i in range(n)]
    last = n - 1
    parts.append(
        f"pub fn main() -> i32\n    let x: E{last} = E{last}.B{last}\n"
        f"    match x\n        E{last}.A{last} => 1\n"
        f"        E{last}.B{last} => 2\n"
    )
    return "\n".join(parts)


def _many_variants(n_enums: int, n_variants: int) -> str:
    parts = []
    for i in range(n_enums):
        body = "".join(f"    V{i}_{j}\n" for j in range(n_variants))
        parts.append(f"enum E{i}\n{body}")
    last = n_enums - 1
    pick = n_variants - 1
    parts.append(
        f"pub fn main() -> i32\n    let x: E{last} = E{last}.V{last}_{pick}\n"
        f"    match x\n        E{last}.V{last}_0 => 1\n"
        f"        E{last}.V{last}_{pick} => 2\n        _ => 3\n"
    )
    return "\n".join(parts)


def _many_locals(n: int) -> str:
    decls = "".join(f"    var v{i}: i64 = {i % 3}\n" for i in range(n))
    # The last-declared local carries the answer.
    return (
        f"pub fn main() -> i32\n{decls}    v{n - 1} = 42\n"
        f"    return (v{n - 1} + v0) as i32\n"
    )


def _many_arms(n: int) -> str:
    """Block-bodied arms that return."""
    arms = "".join(f"        {i} =>\n            return {i % 100}\n" for i in range(n))
    return (
        f"fn pick(x: i64) -> i32\n    match x\n{arms}        _ =>\n            return 101\n"
        "    return 102\n\n"
        f"pub fn main() -> i32\n    return pick({n - 1})\n"
    )


def _many_value_arms(n: int) -> str:
    """A value-yielding match: every arm is a phi incoming edge."""
    arms = "".join(f"        {i} => {i % 100}\n" for i in range(n))
    return (
        f"fn pick(x: i64) -> i64\n    let v: i64 = match x\n{arms}        _ => 101\n"
        "    return v\n\n"
        f"pub fn main() -> i32\n    return pick({n - 1}) as i32\n"
    )


def _many_instantiations(n: int) -> str:
    structs = "".join(f"struct T{i}\n    v: i64\n\n" for i in range(n))
    # One helper per type, so main stays under the 256-locals limit.
    helpers = "".join(
        f"fn get{i}() -> i64\n    let r: T{i} = ident<T{i}>(T{i} {{ v: 1 }})\n    return r.v\n\n"
        for i in range(n)
    )
    calls = "".join(f"    total = total + get{i}()\n" for i in range(n))
    return (
        structs
        + "fn ident<T>(x: T) -> T\n    return x\n\n"
        + helpers
        + f"pub fn main() -> i32\n    var total: i64 = 0\n{calls}"
        + f"    return (total - {n} + 42) as i32\n"
    )


def _long_name_call(n: int) -> str:
    """A call to a struct-returning fn with an n-byte name, bound by an
    unannotated `var`: emit_var_decl's [256]u8 name buffer."""
    fname = "f" + "x" * (n - 1)
    return (
        "struct P\n    a: i64\n    b: i64\n\n"
        f"fn {fname}() -> P\n    return P {{ a: 40, b: 2 }}\n\n"
        f"pub fn main() -> i32\n    var p = {fname}()\n    return (p.a + p.b) as i32\n"
    )


def _deep_nesting(depth: int) -> str:
    lines = ["pub fn main() -> i32", "    var x: i64 = 0"]
    for d in range(depth):
        lines.append("    " * (d + 1) + "if x == 0")
    lines.append("    " * (depth + 1) + "return 42")
    lines.append("    return 1")
    return "\n".join(lines) + "\n"


TAB_PROGRAM = "fn main() -> i32\n\treturn 3\n"


# --- must WORK past the old capacity (ritz0 is the oracle) -------------------

MUST_WORK = {
    # Ticket acceptance: the 17-arg repro exits 17; 33 enums match correctly.
    "args_17": (_many_args(17), 17),
    "args_24": (_many_args(24), 24),
    "method_args_20": (_many_args_method(20), 21),
    "enums_33": (_many_enums(33), 2),
    "enums_40": (_many_enums(40), 2),
    "enum_variants_300": (_many_variants(3, 100), 2),
    "match_value_arms_70": (_many_value_arms(70), 69),
    "match_arms_70": (_many_arms(70), 69),
    "instantiations_270": (_many_instantiations(270), 42),
    "long_name_300": (_long_name_call(300), 42),
}

# --- fixed limits that remain: one located error -----------------------------

MUST_FAIL_LOUD = {
    "locals_300": (_many_locals(300), 42, "too many locals and params in one function"),
    "nesting_70": (_deep_nesting(70), 42, "blocks nested more than 64 levels deep"),
}

ORACLE = {k: v[:2] for k, v in {**MUST_WORK, **MUST_FAIL_LOUD}.items()}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ORACLE))
def test_ritz0_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    program, expected = ORACLE[name]
    assert _run("ritz0", tmp_path, name, program) == expected


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MUST_WORK))
def test_ritz1_past_old_capacity_works(ritz1_bin, tmp_path, name):
    program, expected = MUST_WORK[name]
    assert _run("ritz1", tmp_path, name, program) == expected


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MUST_FAIL_LOUD))
def test_ritz1_fixed_limit_is_a_located_error(ritz1_bin, tmp_path, name):
    program, _, diagnostic = MUST_FAIL_LOUD[name]
    _fails_loud(tmp_path, name, program, diagnostic)


# --- extern declarations: a growable list (was a fixed 2048) -----------------

N_EXTERNS = 2100


@pytest.mark.integration
def test_ritz1_declares_every_extern_past_2048(ritz1_bin, tmp_path):
    """add_extern dropped names past 2048: the calls stayed in the IR but
    their `declare`s did not, so clang rejected the module."""
    lib = "".join(
        f"pub fn ext{i}() -> i64\n    return {i}\n\n" for i in range(N_EXTERNS)
    )
    (tmp_path / "manyext.ritz").write_text(lib)
    calls = "".join(f"    t = t + ext{i}()\n" for i in range(N_EXTERNS))
    program = f"import manyext\n\npub fn main() -> i32\n    var t: i64 = 0\n{calls}    return 0\n"
    comp, ll = _compile("ritz1", tmp_path, "externs", program)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    missing = [i for i in range(N_EXTERNS) if f"declare i64 @ext{i}(" not in ir]
    assert not missing, f"{len(missing)} externs not declared, first: ext{missing[0]}"
    obj = tmp_path / "externs.o"
    cc = subprocess.run(
        ["clang", "-c", str(ll), "-o", str(obj)], capture_output=True, text=True
    )
    assert cc.returncode == 0, cc.stderr[-2000:]


# --- lexer ------------------------------------------------------------------


@pytest.mark.integration
def test_ritz1_tab_indent_is_one_located_error(ritz1_bin, tmp_path):
    """Before #1813 ritz1 printed the lexer error forever and never exited."""
    start = time.monotonic()
    comp, ll = _compile("ritz1", tmp_path, "tab", TAB_PROGRAM, timeout=10)
    elapsed = time.monotonic() - start
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"ritz1 accepted tab indentation:\n{out}"
    # The ticket says 1 s; allow headroom for a loaded CI host.
    assert elapsed < 5, f"tab repro took {elapsed:.1f}s"
    assert "tab.ritz:2:1" in out, f"error is not located:\n{out[-2000:]}"
    assert "Tabs not allowed for indentation" in out, out[-2000:]
    assert out.count("Tabs not allowed") == 1, f"error repeated:\n{out[-2000:]}"
    assert not ll.exists()


# --- symbol maps keyed by a 64-bit hash -------------------------------------

# Two identifiers with the same 64-bit FNV-1a hash (found by a Pollard-rho
# search over "f" + 16 hex digits). Checked below, so a change to the hash
# cannot silently void the tests.
CA, CB = "f04f85380df86b5e1", "f538f6df2280aeeaa"


def _fnv1a64(s: str) -> int:
    h = 0xCBF29CE484222325
    for b in s.encode():
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


# One program per symbol map (fn_map, global_map, struct_map, const_map).
COLLIDE = {
    # Struct return and a u8 param: an unresolved callee falls back to an
    # extern `i64 (i64)` call, which does not match the definition.
    "fn": f"""\
struct P
    a: i64
    b: i64

fn {CA}(x: u8) -> P
    return P {{ a: x as i64, b: 0 }}

fn {CB}(x: u8) -> P
    return P {{ a: 0, b: x as i64 }}

pub fn main() -> i32
    let p: P = {CA}(40)
    let q: P = {CB}(2)
    return (p.a + q.b) as i32
""",
    "global": f"""\
var {CA}: i64 = 40
var {CB}: i64 = 2

pub fn main() -> i32
    return ({CA} + {CB}) as i32
""",
    "struct": f"""\
struct {CA}
    a: i64

struct {CB}
    x: i32
    b: i64

pub fn main() -> i32
    var p: {CA} = {CA} {{ a: 40 }}
    var q: {CB} = {CB} {{ x: 0, b: 2 }}
    return (p.a + q.b) as i32
""",
    "const": f"""\
const {CA}: i64 = 40
const {CB}: i64 = 2

pub fn main() -> i32
    return ({CA} + {CB}) as i32
""",
}


@pytest.mark.unit
def test_colliding_names_really_collide():
    assert CA != CB and _fnv1a64(CA) == _fnv1a64(CB)


@pytest.mark.integration
@pytest.mark.parametrize("kind", sorted(COLLIDE))
def test_ritz0_oracle_hash_collision(tmp_path, kind):
    assert _run("ritz0", tmp_path, f"collide_{kind}", COLLIDE[kind]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("kind", sorted(COLLIDE))
def test_ritz1_hash_collision_resolves_both(ritz1_bin, tmp_path, kind):
    """The find_* symbol maps were keyed by fnv1a(name) alone: the second of
    two colliding names came back as "not found"."""
    assert _run("ritz1", tmp_path, f"collide_{kind}", COLLIDE[kind]) == 42


# --- no debug noise / no silent default arms ---------------------------------


@pytest.mark.integration
def test_ritz1_no_monomorph_debug_prints(ritz1_bin, tmp_path):
    comp, _ = _compile("ritz1", tmp_path, "mono", _many_instantiations(3))
    assert comp.returncode == 0, comp.stderr[-2000:]
    assert "[MONOMORPH]" not in comp.stderr, comp.stderr[-2000:]


@pytest.mark.unit
def test_emit_stmt_default_arm_is_an_error():
    """The default arm of emit_stmt wrote `; TODO: statement kind N` into the
    IR and carried on (the #1369 class). It must go through emit_ir_error."""
    src = (RITZ1_SRC / "emitter_stmt.ritz").read_text()
    assert "TODO: statement kind" not in src
    assert 'emit_ir_error_kind(s, c"unhandled statement kind "' in src
