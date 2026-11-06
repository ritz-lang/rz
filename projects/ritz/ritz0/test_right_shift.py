#!/usr/bin/env python3
"""`>>` is arithmetic on a signed left operand, logical on an unsigned one (#2356).

`(0 - 8) >> 1` on an i64 was -4 on ritz0 and 9223372036854775804 on ritz1, with no
diagnostic on either. The left operand's type decides; the count never does.
ritz1 always emitted `lshr`, and ritz0 fell back to `ashr` for any left operand
that was not a plain name or call, so `(h ^ x) >> 33` on a u64 sign-filled. Each
was right where the other was wrong, which is why neither column of the table
below could be copied from a compiler: every expected value comes from `_shr`.

Const folding runs the host compiler's own `>>`, so ritz1 and ritz1_selfhosted
folded the same source differently. `narrowing.ritz` bounds `<<` with a signed
`>>` too, and that made them disagree on which programs compile. The tables go
through ritz0, ritz1 and ritz1_selfhosted, so they pin that as well.

Not here: a literal in a narrow slot, as in `let r: u8 = (a << 4) >> 4`. ritz0
retypes the literal from the slot and ritz1 has no slot to read, so the two differ
once the left operand leaves the type's range (#2360 asks what the language
should say).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
TYPES = [("i8", 8, True), ("i16", 16, True), ("i32", 32, True), ("i64", 64, True),
         ("u8", 8, False), ("u16", 16, False), ("u32", 32, False), ("u64", 64, False)]


def _wrap(value, bits, signed):
    """`value` as a `bits`-wide integer of that signedness."""
    value &= (1 << bits) - 1
    if signed and value >> (bits - 1):
        value -= 1 << bits
    return value


def _shr(value, count, bits, signed):
    """The spec's `>>`, on Python's unbounded integers: floor for a signed
    `value`, and a non-negative `value` has no sign to fill with."""
    return _wrap(value, bits, signed) >> count


def _forms(ty, bits, signed):
    """name -> (top-level items, body of `fn t() -> i64`, expected as an i64).

    `a` has the type's top bit set, so a shift of the wrong kind is visible.
    """
    v = -8 if signed else (1 << bits) - 8
    top_int = (1 << (bits - 1)) - 1 if signed or bits == 64 else (1 << bits) - 1
    e = _shr(v, 1, bits, signed)
    a = f"let a: {ty} = {v}\n"
    let_r = f"let r: {ty} = "
    ret = "\nr as i64"
    field = f"struct S\n    a: {ty}\n"
    table = {
        # Every way an operand reaches the shift.
        "local": ("", f"{a}{let_r}a >> 1{ret}", e),
        "cast_result": ("", f"{a}(a >> 1) as i64", e),
        "param": (f"fn f(a: {ty}) -> {ty}\n    a >> 1\n", f"f({v}) as i64", e),
        "call": (f"fn g() -> {ty}\n    {v}\n", f"{let_r}g() >> 1{ret}", e),
        "field": (field, f"let s = S {{ a: {v} }}\n{let_r}s.a >> 1{ret}", e),
        "field_ptr": (field, f"var s = S {{ a: {v} }}\nlet p: *S = @s\n{let_r}p.a >> 1{ret}", e),
        "array": ("", f"var x: [2]{ty} = [{v}, 0]\n{let_r}x[0] >> 1{ret}", e),
        "ptr_index": ("", f"var a: {ty} = {v}\nlet p: *{ty} = @a\n{let_r}p[0] >> 1{ret}", e),
        "deref": ("", f"var a: {ty} = {v}\nlet p: *{ty} = @a\n{let_r}*p >> 1{ret}", e),
        "global": (f"var G: {ty} = {v}\n", f"{let_r}G >> 1{ret}", e),
        "const": (f"const C: {ty} = {v}\n", f"{let_r}C >> 1{ret}", e),
        "const_folded": (f"const C: {ty} = {v}\nconst D: {ty} = C >> 1\n", "D as i64", e),
        "cast_operand": ("", f"let w: i64 = {_wrap(v, 64, True)}\n{let_r}(w as {ty}) >> 1{ret}", e),
        "method": (field + f"impl S\n    fn get(self) -> {ty}\n        self.a\n",
                   f"let s = S {{ a: {v} }}\n{let_r}s.get() >> 1{ret}", e),
        "generic": ("fn sh<T>(a: T) -> T\n    a >> 1\n", f"{a}{let_r}sh<{ty}>(a){ret}", e),
        "assign": ("", f"var a: {ty} = {v}\na = a >> 1\na as i64", e),
        "if_value": ("", f"{a}let c: i64 = 1\nlet m: {ty} = if c == 1\n    a\nelse\n    a\n"
                         f"{let_r}m >> 1{ret}", e),

        # The count: width, type and value never choose the kind of shift.
        "count_zero": ("", f"{a}{let_r}a >> 0{ret}", v),
        "count_top": ("", f"{a}{let_r}a >> {bits - 1}{ret}", _shr(v, bits - 1, bits, signed)),
        "count_local": ("", f"{a}let n: {ty} = 1\n{let_r}a >> n{ret}", e),
        "count_i64": ("", f"{a}let n: i64 = 1\n(a >> n) as i64", e),
        "count_u64": ("", f"{a}let n: u64 = 1\n(a >> n) as i64", e),
        "chain": ("", f"{a}{let_r}(a >> 1) >> 1{ret}", _shr(e, 1, bits, signed)),
        "chain_count_u64": ("", f"{a}let n: u64 = 1\n((a >> n) >> 1) as i64",
                            _shr(e, 1, bits, signed)),

        # An expression on the left has its operands' type.
        "xor": ("", f"{a}let z: {ty} = 0\n{let_r}(a ^ z) >> 1{ret}", e),
        "or": ("", f"{a}let z: {ty} = 0\n{let_r}(a | z) >> 1{ret}", e),
        "literal_left": ("", f"{a}{let_r}(1 * a) >> 1{ret}", e),

        # A compare reads the shift's own register, with no store to narrow it.
        "compare_sign": ("", f"{a}var q: i64 = 0\nif (a >> 1) < 0\n    q = 1\nq", int(e < 0)),

        # Past the type's range, which an i64 register can hold and T cannot.
        "wrap_add": ("", f"{a}{let_r}(a + a) >> 1{ret}", _shr(v + v, 1, bits, signed)),
        "wrap_not": ("", f"{a}{let_r}(~a) >> 1{ret}", _shr(~v, 1, bits, signed)),
        "wrap_sub": ("", f"let a: {ty} = 1\nlet c: {ty} = 2\n{let_r}(a - c) >> 1{ret}",
                     _shr(-1, 1, bits, signed)),
        "overflow": ("", f"let a: {ty} = {top_int}\n{let_r}(a + a) >> 1{ret}",
                     _shr(2 * top_int, 1, bits, signed)),
    }
    # Beside an i64 the expression is an i64, unless this is a u64: at equal
    # width the unsigned side wins, as it does for `/` and `<` (#1604).
    mixed = e if bits == 64 or signed else _shr(v, 1, 64, True)
    table["mixed_right"] = ("", f"{a}let k: i64 = 0\n((a + k) >> 1) as i64", mixed)
    table["mixed_left"] = ("", f"{a}let k: i64 = 0\n((k + a) >> 1) as i64", mixed)
    if signed:
        table["negate"] = ("", f"let a: {ty} = 8\n{let_r}(-a) >> 1{ret}", -4)
    return {name: (top, body, _wrap(want, 64, True)) for name, (top, body, want) in table.items()}


def _u64_reach():
    """The u64 forms an i64 default would sign-fill. Each got `ashr` on ritz1 from
    the first `ashr` fix, because nothing there types them, or on ritz0 before."""
    v = (1 << 64) - 8
    e = _shr(v, 1, 64, False)
    a = f"let a: u64 = {v}\n"
    let_r = "let r: u64 = "
    ret = "\nr as i64"
    field = "struct S\n    a: u64\n"
    # A Vec over a local array: the index sugar without an allocator to link.
    vec = f"var d: [1]u64 = [{v}]\nvar x = Vec<u64> {{ data: @d[0], len: 1, cap: 1 }}\n"
    get = field + "impl S\n    fn get(self) -> u64\n        self.a\n"
    table = {
        "array_field": ("struct Q\n    x: [2]u64\n",
                        f"var q = Q {{ x: [{v}, 0] }}\n{let_r}q.x[0] >> 1{ret}"),
        "ptr_field_index": ("struct Q\n    x: *u64\n",
                            f"var a: u64 = {v}\nvar q = Q {{ x: @a }}\n{let_r}q.x[0] >> 1{ret}"),
        "element_field": (field, f"var x: [1]S = [S {{ a: {v} }}]\n{let_r}x[0].a >> 1{ret}"),
        "nested_field": (field + "struct N\n    s: S\n",
                         f"let n = N {{ s: S {{ a: {v} }} }}\n{let_r}n.s.a >> 1{ret}"),
        "deref_member": (field, f"var s = S {{ a: {v} }}\nlet p: *S = @s\n{let_r}(*p).a >> 1{ret}"),
        "deref_add": ("", f"var x: [2]u64 = [0, {v}]\nlet p: *u64 = @x[0]\n{let_r}*(p + 1) >> 1{ret}"),
        "deref_cast": ("", f"var a: u64 = {v}\nlet p: *u8 = (@a) as *u8\n{let_r}*(p as *u64) >> 1{ret}"),
        "deref_field": ("struct Q\n    p: *u64\n",
                        f"var a: u64 = {v}\nlet q = Q {{ p: @a }}\n{let_r}*q.p >> 1{ret}"),
        "deref_twice": ("", f"var a: u64 = {v}\nvar p: *u64 = @a\nlet pp: **u64 = @p\n{let_r}**pp >> 1{ret}"),
        "global_array": ("var G: [2]u64\n", f"G[0] = {v}\n{let_r}G[0] >> 1{ret}"),
        "const_array": (f"const K: [1]u64 = [{v}]\n", f"{let_r}K[0] >> 1{ret}"),
        "ref": ("fn f(a: @u64) -> u64\n    *a >> 1\n", f"{a}f(@a) as i64"),
        "mut_ref": ("fn f(a: @&u64) -> u64\n    *a >> 1\n", f"var a: u64 = {v}\nf(@&a) as i64"),
        "ptr_param": ("fn f(a: *u64, i: i64) -> u64\n    a[i] >> 1\n",
                      f"var x: [1]u64 = [{v}]\nf(@x[0], 0) as i64"),
        "self_field": (field + "impl S\n    fn h(self) -> u64\n        self.a >> 1\n",
                       f"let s = S {{ a: {v} }}\ns.h() as i64"),
        "static_method": (field + f"impl S\n    fn mk() -> u64\n        {v}\n",
                          f"{let_r}S.mk() >> 1{ret}"),
        "fn_pointer": (f"fn g() -> u64\n    {v}\n",
                       f"let f: fn() -> u64 = g\n{let_r}f() >> 1{ret}"),
        "generic_field": ("struct W<T>\n    v: T\n",
                          f"let w = W<u64> {{ v: {v} }}\n{let_r}w.v >> 1{ret}"),
        "vec_index": ("", f"{vec}{let_r}x[0] >> 1{ret}"),
        "vec_field": ("struct Q\n    x: Vec<u64>\n",
                      f"{vec}var q = Q {{ x: x }}\n{let_r}q.x[0] >> 1{ret}"),
        "vec_ref": ("fn f(x: @Vec<u64>) -> u64\n    x[0] >> 1\n", f"{vec}f(@x) as i64"),
        "generic_call": ("fn id<T>(a: T) -> T\n    a\n", f"{a}{let_r}id<u64>(a) >> 1{ret}"),
        "inferred_name": ("", f"{a}let b = a\n{let_r}b >> 1{ret}"),
        "inferred_call": (f"fn g() -> u64\n    {v}\n", f"let b = g()\n{let_r}b >> 1{ret}"),
        "inferred_operator": ("", f"{a}let b = a ^ 0\n{let_r}b >> 1{ret}"),
        "inferred_method": (get, f"let s = S {{ a: {v} }}\nlet b = s.get()\n{let_r}b >> 1{ret}"),
    }
    return {name: (top, body, _wrap(e, 64, True)) for name, (top, body) in table.items()}


def _indent(body):
    return "".join(f"    {line}\n" for line in body.split("\n"))


def _program(forms):
    """Every form in one program: exit 0, or the 1-based index of the first form
    whose value is wrong."""
    parts, calls = [], []
    for i, (name, (top, body, want)) in enumerate(forms.items(), 1):
        # Items are renamed per form, so one program can hold all of them.
        for word in ("S", "G", "C", "D", "K", "N", "Q", "W", "f", "g", "id", "sh"):
            top = _rename(top, word, f"{word}{i}")
            body = _rename(body, word, f"{word}{i}")
        parts.append(f"{top}fn t{i}() -> i64\n{_indent(body)}")
        calls.append(f"    if t{i}() != {want}\n        return {i}\n")
    return "import ritzlib.gvec\n" + "".join(parts) + "fn main() -> i32\n" + "".join(calls) + "    0\n"


def _rename(text, word, new):
    return re.sub(rf"(?<![\w.]){word}\b", new, text)


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


def _run(request, compiler, tmp_path, source):
    proc, ll = _compile(request, compiler, tmp_path, source)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    exe = tmp_path / "unit"
    link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link.insert(2, str(RITZ_START))
    built = subprocess.run(link, cwd=tmp_path, capture_output=True, text=True)
    assert built.returncode == 0, f"{compiler}: link:\n{built.stderr[-1500:]}"
    return subprocess.run([str(exe)], timeout=60).returncode


def _main(body):
    return "fn main() -> i32\n" + _indent(body)


# Whole programs: name -> (source, exit code).
EXACT = {
    # The ticket's repro.
    "ticket": (_main("let b: i64 = 0 - 8\nlet c: i64 = b >> 1\nif c < 0\n    return 3\n4"), 3),

    # A left literal is an i64, unless only a u64 can hold it.
    "literal_negative": (_main("let x: i64 = -8 >> 1\nif x == -4\n    return 0\n1"), 0),
    "literal_subtraction": (_main("let x: i64 = (0 - 8) >> 1\nif x == -4\n    return 0\n1"), 0),
    "literal_past_i64": (_main("let x: u64 = 0xF000000000000000 >> 60\nx as i32"), 15),

    # The folders, which ran the host compiler's `>>` on an untyped value.
    "fold_signed": ("const C: i64 = -8\nconst D: i64 = C >> 1\n"
                    + _main("if D == -4\n    return 0\n1"), 0),
    "fold_literal": ("const D: i64 = (0 - 8) >> 1\n" + _main("if D == -4\n    return 0\n1"), 0),
    "fold_u64_literal": ("const D: i64 = 0xF000000000000000 >> 60\n" + _main("D as i32"), 15),
    "fold_u64_hex": ("const C: u64 = 0xFFFFFFFFFFFFFFF8\nconst D: i64 = (C >> 60) as i64\n"
                     + _main("D as i32"), 15),
    "fold_u64_computed": ("const C: u64 = 0xFFFFFFFFFFFFFFF0 | 8\nconst D: u64 = C >> 60\n"
                          + _main("D as i32"), 15),
    "fold_u64_cast": ("const D: i64 = ((0 - 8) as u64 >> 60) as i64\n" + _main("D as i32"), 15),

    # narrowing.ritz's bound on `<<` is itself a signed `>>`: built by ritz1 it
    # was a huge positive number, so ritz1_selfhosted rejected this and ritz1 did not.
    "narrow_bound": (_main("let x: i8 = (0 - 8) << 2\nif x == -32\n    return 0\n1"), 0),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty,bits,signed", TYPES, ids=[t[0] for t in TYPES])
def test_every_form_at_every_width(request, compiler, tmp_path, ty, bits, signed):
    forms = _forms(ty, bits, signed)
    code = _run(request, compiler, tmp_path, _program(forms))
    wrong = list(forms)[code - 1] if 0 < code <= len(forms) else code
    assert code == 0, f"{compiler}, {ty}: {wrong}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_way_to_reach_a_u64(request, compiler, tmp_path):
    forms = _u64_reach()
    code = _run(request, compiler, tmp_path, _program(forms))
    wrong = list(forms)[code - 1] if 0 < code <= len(forms) else code
    assert code == 0, f"{compiler}: {wrong}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(EXACT))
def test_exact_programs(request, compiler, tmp_path, name):
    source, code = EXACT[name]
    assert _run(request, compiler, tmp_path, source) == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_there_is_no_shift_assignment(request, compiler, tmp_path):
    """Section 4.2: `>>=` is not an operator, so nothing can disagree about it."""
    proc, _ = _compile(request, compiler, tmp_path, _main("var x: i64 = 8\nx >>= 1\nx as i32"))
    assert proc.returncode != 0


def test_the_oracle_is_the_rule():
    """`_shr` is what the tables trust, so it is checked by hand."""
    assert _shr(-8, 1, 64, True) == -4
    assert _shr(-1, 63, 64, True) == -1
    assert _shr(-8, 1, 8, True) == -4
    assert _shr((1 << 64) - 8, 1, 64, False) == (1 << 63) - 4
    assert _shr(248, 1, 8, False) == 124
    assert _shr(~248, 1, 8, False) == 3
