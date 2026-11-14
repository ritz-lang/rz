#!/usr/bin/env python3
"""A generic user enum's instance is a laid-out enum on ritz1 too (AGAST #2422).

`enum Slot<T>` used as `Slot<i32>`: ritz1 recorded the template with `T`
unsubstituted and never declared `%Slot$i32`, so a fn taking one was IR clang
refused (`invalid type for function argument`), and `Full(5)` lowered to a
call to an undefined `@Full`.  ritz0 lays the instance out as it would the enum
with `T` written in: `{ i8 tag, [pad x i8], [N x i8] payload }`.

ritz1 now records each instance a program names as a concrete enum of that
name (monomorph's add_enum_instance), with its payload fields substituted, and
a bare constructor builds the instance its slot names: the typed let's, the
parameter's, the field's, the assignment target's, or the fn's return type.

Each row runs on all three compilers, the expected code from what the program
says.  Every row separates a path: a row that only repeated another's was left
out (docs/TESTING.md, "What a ritz0 pytest case costs").

A payload named like a const or variant on an instance (`Full(K)` on
`Slot<i32>`) is the binder's R12 error, as on any enum:
test_variant_payload_refused.py holds those rows.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import batching
import fast_link
from ritz0_inproc import run_ritz0

pytestmark = [pytest.mark.integration, pytest.mark.batched]

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

SLOT = "enum Slot<T>\n    Full(T)\n    Empty\n"
# `g` reads an Option<i32>'s payload, 3 for None (AGAST #2987).
G = "fn g(x: Option<i32>) -> i32\n    match x\n        Some(v) => v\n        None => 3\n"
# `f` reads a Slot<i32>'s payload, 2 for Empty.
F = "fn f(o: Slot<i32>) -> i32\n    match o\n        Full(v) => v\n        Empty => 2\n"

# name -> (program, exit code)
RUNS = {
    # The ticket's: a parameter, a typed let's constructor, a match.
    "parameter": (SLOT + F + "fn main() -> i32\n    let s: Slot<i32> = Full(5)\n    f(s)\n", 5),
    "match_on_a_local": (SLOT + "fn main() -> i32\n    let s: Slot<i32> = Full(5)\n"
                         "    match s\n        Full(v) => v + 1\n        _ => 2\n", 6),
    # A unit variant is an identifier, not a call.
    "unit_variant": (SLOT + F + "fn main() -> i32\n    let s: Slot<i32> = Empty\n    f(s)\n", 2),
    # Each slot a bare constructor can take its instance from.
    "argument": (SLOT + F + "fn main() -> i32\n    f(Full(5)) * 10 + f(Empty)\n", 52),
    "return_and_tail": (SLOT + F + "fn mk(n: i32) -> Slot<i32>\n    if n > 0\n"
                        "        return Full(n)\n    Empty\n"
                        "fn main() -> i32\n    f(mk(6)) * 10 + f(mk(0))\n", 62),
    "struct_field": (SLOT + F + "struct H\n    s: Slot<i32>\n    n: i32\n"
                     "fn main() -> i32\n    let h = H { s: Full(8), n: 1 }\n    f(h.s) + h.n\n", 9),
    "assignment": (SLOT + F + "fn main() -> i32\n    var s: Slot<i32> = Empty\n"
                   "    let a: i32 = f(s)\n    s = Full(9)\n    a * 10 + f(s)\n", 29),
    # Layout: the payload's own size and alignment, per instance.
    "two_instances": (SLOT + F + "fn g(o: Slot<u8>) -> i32\n    match o\n"
                      "        Full(v) => v as i32\n        _ => 3\n"
                      "fn main() -> i32\n    let a: Slot<i32> = Full(5)\n"
                      "    let b: Slot<u8> = Full(200 as u8)\n    f(a) + g(b) - 200\n", 5),
    "wide_payload": (SLOT + "fn f(o: Slot<i64>) -> i64\n    match o\n        Full(v) => v\n"
                     "        _ => 2\nfn main() -> i32\n    let s: Slot<i64> = Full(0x100000009)\n"
                     "    (f(s) - 0x100000000) as i32\n", 9),
    "struct_payload": ("struct P\n    a: u8\n    b: i64\n" + SLOT +
                       "fn f(o: Slot<P>) -> i32\n    match o\n"
                       "        Full(p) => p.a as i32 + p.b as i32\n        _ => 2\n"
                       "fn main() -> i32\n    let s: Slot<P> = Full(P { a: 3 as u8, b: 4 })\n"
                       "    f(s)\n", 7),
    "two_parameters": ("enum Two<A, B>\n    L(A)\n    R(B)\n"
                       "fn f(t: Two<u8, i64>) -> i32\n    match t\n"
                       "        L(a) => a as i32\n        R(b) => b as i32 + 100\n"
                       "fn main() -> i32\n    let x: Two<u8, i64> = L(4 as u8)\n"
                       "    let y: Two<u8, i64> = R(5)\n    f(x) * 1000 + f(y)\n", 9),
    # An instance only another's payload names; splitting `$Slot$u8$i64`
    # into Two's two arguments needs Slot's arity.
    "only_a_payload_names_it": (
        SLOT + "enum Two<A, B>\n    L(A)\n    R(B)\nfn f(t: Two<Slot<u8>, i64>) -> i32\n"
        "    match t\n        L(s) =>\n            match s\n                Full(v) => v as i32\n"
        "                Empty => 3\n        R(b) => b as i32 + 100\n"
        "fn main() -> i32\n    let y: Two<Slot<u8>, i64> = R(5)\n    f(y)\n", 105),
    # An instance only a generic struct's instance names.
    "generic_struct_field": (SLOT + "struct W<T>\n    s: Slot<T>\n    n: i32\n"
                             "fn h<T>(w: W<T>) -> i32\n    w.n\nfn main() -> i32\n"
                             "    var w: W<i32>\n    w.n = 3\n    h<i32>(w)\n", 3),
    # An instance whose payload is another.
    "nested": (SLOT + "fn f(o: Slot<Slot<i32>>) -> i32\n    match o\n        Full(i) =>\n"
               "            match i\n                Full(v) => v\n                Empty => 3\n"
               "        Empty => 4\nfn main() -> i32\n    let i: Slot<i32> = Full(7)\n"
               "    let a: Slot<Slot<i32>> = Full(i)\n    f(a)\n", 7),
    # An instance only a specialised generic fn's signature names.
    "generic_fn": (SLOT + "fn g<T>(o: Slot<T>) -> i32\n    match o\n        Full(v) => 1\n"
                   "        Empty => 2\nfn main() -> i32\n    let a: Slot<i64> = Full(5)\n"
                   "    let b: Slot<i64> = Empty\n    g<i64>(a) * 10 + g<i64>(b)\n", 12),
    # A concrete enum declaring `Full` too: each slot picks its own, and an
    # instance declares no variant of its own, so a `Q` slot's `Full` is Q's.
    "beside_a_concrete_enum": (SLOT + "enum Q\n    Full(i32)\n    Nope\n" + F +
                               "fn g(q: Q) -> i32\n    match q\n        Full(v) => v\n"
                               "        Nope => 3\nfn main() -> i32\n"
                               "    let a: Slot<i32> = Full(5)\n    let q: Q = Full(4)\n"
                               "    f(a) * 10 + g(q)\n", 54),
    # AGAST #2926: a bare constructor as a variant's payload builds the
    # payload's declared type, as an argument builds its parameter's: an
    # instance's `Full(Some(6))`, and a concrete enum's `Has(Some(6))` /
    # `Has(None)`.  ritz1 gave the payload no slot and refused the inner one.
    "constructor_payload": (SLOT + "fn f(o: Slot<Option<i32>>) -> i32\n    match o\n"
                            "        Full(x) =>\n            match x\n                Some(v) => v\n"
                            "                None => 3\n        Empty => 4\n"
                            "fn main() -> i32\n    let a: Slot<Option<i32>> = Full(Some(6))\n"
                            "    f(a)\n", 6),
    "concrete_constructor_payload": ("enum H\n    Has(Option<i32>)\n    Lacks\n"
                                     "fn f(o: H) -> i32\n    match o\n        Has(x) =>\n"
                                     "            match x\n                Some(v) => v\n"
                                     "                None => 3\n        Lacks => 4\n"
                                     "fn main() -> i32\n    let a: H = Has(Some(6))\n"
                                     "    let b: H = Has(None)\n    f(a) * 10 + f(b)\n", 63),
    # AGAST #2927: an untyped `let` / `var` bound to a bare constructor is the
    # instance its payload binds, as a generic call's T is (LANGUAGE_SPEC
    # section 4.4).  ritz0 crashed (`Unknown function: Full`, no location) and
    # ritz1 called an undefined `@Full`.  A literal is an i64...
    "untyped_let": (SLOT + "fn main() -> i32\n    let s = Full(5)\n    match s\n"
                    "        Full(v) => v\n        _ => 2\n", 5),
    "untyped_let_literal_is_i64": (SLOT + "fn f(o: Slot<i64>) -> i64\n    match o\n"
                                   "        Full(v) => v\n        _ => 2\n"
                                   "fn main() -> i32\n    let s = Full(0x100000009)\n"
                                   "    (f(s) - 0x100000000) as i32\n", 9),
    # ...a typed local its own type, and a `var` can be reassigned.
    "untyped_let_takes_the_payloads_type": (SLOT + F + "fn main() -> i32\n"
                                            "    let x: i32 = 6\n    let s = Full(x)\n    f(s)\n", 6),
    "untyped_var": (SLOT + "fn main() -> i32\n    var s = Full(5)\n    s = Empty\n"
                    "    match s\n        Full(v) => v as i32\n        Empty => 7\n", 7),
    # The fn's return type, when it is an instance of the variant's enum, as
    # #2430 has it for `let o = Some(5)` in a `-> Option<i32>` fn.
    "untyped_let_in_a_fn_returning_it": (SLOT + F + "fn mk() -> Slot<i32>\n    let s = Full(5)\n"
                                         "    s\nfn main() -> i32\n    f(mk())\n", 5),
    # A concrete enum declaring the variant too keeps it, as before.
    "untyped_let_beside_a_concrete_enum": (SLOT + "enum Q\n    Full(i32)\n    Nope\n"
                                           "fn main() -> i32\n    let q = Full(4)\n    match q\n"
                                           "        Full(v) => v\n        Nope => 3\n", 4),
    # In a generic fn the payload's T is the fn's, substituted per instance.
    "untyped_let_in_a_generic_fn": (SLOT + "fn g<T>(x: T) -> i32\n    let s = Full(x)\n"
                                    "    match s\n        Full(v) => 1\n        Empty => 2\n"
                                    "fn main() -> i32\n    let a: u8 = 3\n    g<i32>(4) * 10 + g<u8>(a)\n",
                                    11),
    # AGAST #2987: a builtin's payload declared as an enum is that aggregate,
    # stored and bound so whatever the payload's expression form: a ctor or a
    # local of `Option<i32>`, or a call or deref yielding a user enum.  ritz1 stored it as an i64
    # (invalid IR) and bound it as one.
    "result_carrying_options": (G + "fn f(o: Result<Option<i32>, Option<i32>>) -> i32\n"
                                "    match o\n        Ok(x) => g(x)\n        Err(x) => g(x) + 1\n"
                                "fn main() -> i32\n"
                                "    let a: Result<Option<i32>, Option<i32>> = Ok(Some(6))\n"
                                "    let b: Result<Option<i32>, Option<i32>> = Ok(None)\n"
                                "    let c: Result<Option<i32>, Option<i32>> = Err(Some(1))\n"
                                "    let d: Result<Option<i32>, Option<i32>> = Err(None)\n"
                                "    f(a) * 1000 + f(b) * 100 + f(c) * 10 + f(d)\n", 6324 % 256),
    "option_of_option_by_name": (G + "fn wrap(h: Option<i32>) -> Option<Option<i32>>\n    Some(h)\n"
                                 "fn f(o: Option<Option<i32>>) -> i32\n    match o\n"
                                 "        Some(x) => g(x)\n        None => 4\n"
                                 "fn main() -> i32\n    f(wrap(Some(6))) * 10 + f(wrap(None))\n", 63),
    "option_of_user_enum_by_deref_and_call": ("enum H\n    Has(i32)\n    Lacks\n"
                                              "fn g(x: H) -> i32\n    match x\n        Has(v) => v\n"
                                              "        Lacks => 3\nfn pick() -> H\n    Has(6)\n"
                                              "fn f(o: Option<H>) -> i32\n    match o\n        Some(x) => g(x)\n"
                                              "        None => 4\nfn main() -> i32\n    let h: H = Lacks\n"
                                              "    let p: *H = @h\n    let a: Option<H> = Some(pick())\n"
                                              "    let b: Option<H> = Some(*p)\n    f(a) * 10 + f(b)\n", 63),
    # AGAST #2435: a nested literal whose inner enum nothing else names.  ritz1
    # declared the outer `%Option$Option$i32` only, and its build allocas the
    # inner `%Option$i32`: unsized, clang refused it.  T's side, then E's.
    "literal_nested_option": ("fn f(o: Option<Option<i32>>) -> i32\n    match o\n"
                              "        Some(x) =>\n            match x\n"
                              "                Some(v) => v\n                None => 3\n"
                              "        None => 4\nfn main() -> i32\n"
                              "    let a: Option<Option<i32>> = Some(Some(6))\n"
                              "    let b: Option<Option<i32>> = Some(None)\n    f(a) * 10 + f(b)\n", 63),
    # AGAST #2437: a bare constructor as a match scrutinee has no slot, so the
    # payload binds T as for an untyped let (LANGUAGE_SPEC section 11.3), and
    # the fn's return type has no say: the scrutinee isn't its value (#2419).
    # ritz0 crashed (`Unknown function: Full`), ritz1 linked against `@Full`.
    "scrutinee": (SLOT + "fn main() -> i32\n    match Full(5)\n"
                  "        Full(v) => v as i32\n        Empty => 2\n", 5),
    "scrutinee_literal_is_i64_whatever_the_fn_returns": (
        SLOT + F + "fn mk() -> Slot<i32>\n    var r: i32 = 0\n    match Full(0x100000009)\n"
        "        Full(v) =>\n            r = (v >> 32) as i32\n        Empty =>\n            r = 2\n"
        "    Full(r)\nfn main() -> i32\n    f(mk())\n", 1),
    "scrutinee_takes_the_payloads_type": (SLOT + "fn main() -> i32\n    let x: u8 = 200\n"
                                          "    match @Full(x)\n        Full(v) => v as i32 - 190\n"
                                          "        Empty => 2\n", 10),
    "scrutinee_in_a_generic_fn": (SLOT + "fn g<T>(x: T) -> i32\n    match Full(x)\n"
                                  "        Full(v) => 1\n        Empty => 9\n"
                                  "fn main() -> i32\n    let a: u8 = 3\n    g<i64>(4) * 10 + g<u8>(a)\n",
                                  11),
    "literal_option_as_err": ("fn main() -> i32\n    let r: Result<i32, Option<i64>> = Err(Some(5))\n"
                              "    match r\n        Ok(v) => 1\n        Err(x) =>\n"
                              "            match x\n                Some(v) => v as i32\n"
                              "                None => 3\n", 5),
}


def _emit(compiler, path, ll, work):
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{work}")
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=work, env=env,
                          capture_output=True, text=True, timeout=300)


def _link(compiler, ll, work):
    exe = work / "main"
    cmd = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        cmd.insert(2, str(RITZ_START))
    return fast_link.clang(cmd, cwd=work, capture_output=True, text=True), exe


def _batch_compile(compiler, path, work):
    """batching.run's `compile`: the compile alone, into `work/main.ll` (AGAST #2867)."""
    comp = _emit(compiler, path, work / "main.ll", work)
    return comp.returncode, comp.stdout + comp.stderr


def _batch_build(compiler, path, work):
    """batching.run's `build`: compile and link a batch the way `_run` does a row."""
    ll = work / "main.ll"
    code, output = _batch_compile(compiler, path, work)
    if code != 0 or not ll.exists():
        return False, output, None
    link, exe = _link(compiler, ll, work)
    return link.returncode == 0, link.stderr, exe


def _run(compiler, work, src, modules=None):
    if modules is None:
        got = batching.run(compiler, src, _batch_build, compile=_batch_compile)  # #2806, #2867
        if got is not None:
            return got
    batching.per_row()
    for name, text in (modules or {}).items():
        (work / name).write_text(text)
    path, ll = work / "main.ritz", work / "main.ll"
    path.write_text(src)
    comp = _emit(compiler, path, ll, work)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused:\n{src}\n{out[-2000:]}"
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, f"{compiler}: would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], timeout=60).returncode


@pytest.fixture
def need_ritz1(request):
    def need(compiler):
        if compiler != "ritz0":
            request.getfixturevalue("ritz1_bin")
    return need


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_an_instance_runs_as_ritz0_runs_it(tmp_path, need_ritz1, compiler, name):
    need_ritz1(compiler)
    src, code = RUNS[name]
    assert _run(compiler, tmp_path, src) == code, f"{compiler}, {name}"


# AGAST #2437: `match Full(x)`, x a u8, builds a `Slot<u8>` even beside a
# `Slot<i64>` the module names after it; ritz0's emitter took the last instance
# declaring `Full`.  Only the binding's size tells them apart, and ritz1 sizes
# every payload binding as an i64 (#3116), though it builds `Slot$u8`.
@pytest.mark.parametrize("compiler", [
    "ritz0",
    *(pytest.param(c, marks=pytest.mark.xfail(strict=True, reason="AGAST #3116"))
      for c in ("ritz1", "ritz1_selfhosted"))])
def test_ritz0_builds_the_scrutinees_own_instance(tmp_path, need_ritz1, compiler):
    need_ritz1(compiler)
    src = (SLOT + "fn main() -> i32\n    let s: Slot<u8> = Full(200 as u8)\n"
           "    let t: Slot<i64> = Full(5)\n    let x: u8 = 200\n    match Full(x)\n"
           "        Full(v) => sizeof(v) as i32\n        Empty => 2\n")
    assert _run(compiler, tmp_path, src) == 1, compiler


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_imported_generic_enum_is_instantiated_here(tmp_path, need_ritz1, compiler):
    """The template is another module's; its instance is this compile's."""
    need_ritz1(compiler)
    module = "pub enum Box2<T>\n    Has(T)\n    Nil\n"
    src = ("import gm\nfn f(o: Box2<i32>) -> i32\n    match o\n        Has(v) => v\n"
           "        Nil => 2\nfn main() -> i32\n    let a: Box2<i32> = Has(8)\n    f(a)\n")
    assert _run(compiler, tmp_path, src, {"gm.ritz": module}) == 8, compiler


# AGAST #2927: an untyped let whose constructor leaves a type parameter
# unbound is the section 4.4 error at the constructor, on all three compilers.
# name -> (main's body, line:col of the constructor, type param, variant)
UNINFERABLE = {
    "unit_variant": ("    let s = Empty\n    0\n", "8:13", "T", "Empty"),
    "unit_variant_var": ("    var s = Empty\n    0\n", "8:13", "T", "Empty"),
    "a_param_the_payload_leaves": ("    let t = L(4)\n    0\n", "8:13", "B", "L"),
    # AGAST #2437: a match scrutinee, as `let` above.
    "unit_variant_scrutinee": ("    match Empty\n        Full(v) => 1\n        Empty => 2\n",
                               "8:11", "T", "Empty"),
    "a_param_the_scrutinee_leaves": ("    match L(4)\n        L(a) => 1\n        R(b) => 2\n",
                                     "8:11", "B", "L"),
}
TWO = "enum Two<A, B>\n    L(A)\n    R(B)\n"


def _uninferable_message(tp, variant):
    return f"can't infer `{tp}` for `{variant}`: give the binding a type"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(UNINFERABLE))
def test_an_uninferable_constructor_is_refused_at_it(tmp_path, need_ritz1, compiler, name):
    need_ritz1(compiler)
    body, where, tp, variant = UNINFERABLE[name]
    src = SLOT + TWO + "fn main() -> i32\n" + body
    at = tuple(map(int, where.split(":")))
    got = batching.refused(compiler, src, _batch_compile, at=at)
    if got is not None:  # AGAST #2806: this row's diagnostics from its chunk's batch
        out, where = got
    else:
        batching.per_row()
        path, ll = tmp_path / "main.ritz", tmp_path / "main.ll"
        path.write_text(src)
        comp = _emit(compiler, path, ll, tmp_path)
        out = comp.stdout + comp.stderr
        assert comp.returncode != 0, f"{compiler} accepted {name}:\n{src}\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, _uninferable_message(tp, variant)) in found, \
        f"{compiler}: {name}, wanted {where}:\n{src}\n{out[-2000:]}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_refused_unit_scrutinee_is_the_only_error(tmp_path, need_ritz1, compiler):
    """AGAST #2437: `match Empty` is refused at `Empty`, and that is all: ritz1
    went on to emit it and trailed an unlocated `unknown identifier 'Empty'`.
    Unbatched: a batch hands back only the row's located diagnostics."""
    need_ritz1(compiler)
    src = SLOT + "fn main() -> i32\n    match Empty\n        Full(v) => 1\n        Empty => 2\n"
    path, ll = tmp_path / "main.ritz", tmp_path / "main.ll"
    path.write_text(src)
    comp = _emit(compiler, path, ll, tmp_path)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted it:\n{out}"
    assert "main.ritz:5:11: " in out and _uninferable_message("T", "Empty") in out, out
    assert "unknown identifier" not in out and "cannot emit" not in out, f"{compiler}:\n{out}"
