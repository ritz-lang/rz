#!/usr/bin/env python3
"""A local can't take the name of a const, global or variant (AGAST #2407, LARB R12).

A bare read of a name that was both a local and a module value read whichever the
compiler looked at first, and they disagreed:

    const K: i32 = 7
    fn main() -> i32
        let K: i32 = 3
        K               # 7 on every compiler: the const won

a local over a global read the local, and `for v in g` read ritz0's global but
ritz1's local (#2386).  The ruling removes the question: a local binding (`let`,
`var`, a param, a `for` variable, a match arm's name, a variant payload's name)
that takes the name of a `const`, a global `var` or an enum variant, declared in
the file or imported, is a located error at the name, on all three compilers.
§10.2's "a local named like a variant shadows it" is gone (Aaron, 2026-11-08,
#2455): a name has one meaning.

A fn name stays legal, and the local wins: a call says it wants a fn.  So calling a
local that holds no fn value is an error too; ritz0 called the fn and ritz1 jumped
to the integer.

The expected exit codes below come from what each program says, not from a
compiler.  Every row runs on ritz0, ritz1 and ritz1_selfhosted.
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

# Every row compiles beside this module, as `pm`.
_MODULE = "pub const MK: i32 = 7\npub var MG: i32 = 7\npub enum MC\n    MR\n    MS\n"

# name -> (what it is, the declarations that make it one, or an import)
_OWNERS = {
    "const": ("const", "const K: i32 = 7\n", "K"),
    "global": ("global", "var G: i32 = 7\n", "G"),
    "variant": ("variant", "enum C\n    R\n    S\n", "R"),
    "builtin_variant": ("variant", "", "None"),
    "imported_const": ("const", "import pm\n", "MK"),
    "imported_global": ("global", "import pm\n", "MG"),
    "imported_variant": ("variant", "import pm\n", "MR"),
    "ritzlib_const": ("const", "import ritzlib.sys\n", "SYS_READ"),
}

# The scrutinee of the arm row: an enum the name is no variant of.
_D = "enum D\n    X\n    Y\n"


def _binders(name):
    """binder kind -> (program after the declarations, line of the name, column).

    Lines count from 1 at the first line after the declarations."""
    return {
        "let": (f"fn main() -> i32\n    let {name}: i32 = 3\n    0\n", 2, 9),
        "untyped_let": (f"fn main() -> i32\n    let {name} = 3\n    0\n", 2, 9),
        "var": (f"fn main() -> i32\n    var {name}: i32 = 3\n    0\n", 2, 9),
        "param": (f"fn g({name}: i32) -> i32\n    0\nfn main() -> i32\n    g(3)\n", 1, 6),
        "second_param": (f"fn g(a: i32, {name}: i32) -> i32\n    a\n"
                         f"fn main() -> i32\n    g(3, 4)\n", 1, 14),
        "for_range": (f"fn main() -> i32\n    var t: i32 = 0\n    for {name} in 0..3\n"
                      f"        t = t + 1\n    t\n", 3, 9),
        "for_array": (f"fn main() -> i32\n    let a: [2]i32 = [1, 2]\n    var t: i32 = 0\n"
                      f"    for {name} in a\n        t = t + 1\n    t\n", 4, 9),
        "payload": (f"fn f(o: Option<i32>) -> i32\n    match o\n        Some({name}) => 1\n"
                    f"        _ => 2\nfn main() -> i32\n    f(Some(5))\n", 3, 14),
        # An integer const too: against an enum it compares nothing.
        "arm": (_D + f"fn f(d: D) -> i32\n    match d\n        X => 1\n        {name} => 2\n"
                f"fn main() -> i32\n    f(D.Y)\n", 7, 9),
        "method_param": (f"struct T\n    v: i32\nimpl T\n    fn m(self, {name}: i32) -> i32\n"
                         f"        self.v\nfn main() -> i32\n    let t = T {{ v: 1 }}\n"
                         f"    t.m(2)\n", 4, 16),
        "generic_fn": (f"fn g<T>(x: T) -> i32\n    let {name}: i32 = 3\n    0\n"
                       f"fn main() -> i32\n    g<i32>(1)\n", 2, 9),
        "nested_block": (f"fn main() -> i32\n    var t: i32 = 0\n    if t == 0\n"
                         f"        let {name}: i32 = 3\n        t = 1\n    t\n", 4, 13),
        "match_arm_body": (f"fn f(o: Option<i32>) -> i32\n    match o\n        Some(v) =>\n"
                           f"            let {name}: i32 = v\n            1\n        _ => 2\n"
                           f"fn main() -> i32\n    f(Some(5))\n", 4, 17),
    }


def _message(kind, name):
    return f"a local can't take the name of a {kind}: '{name}' — rename the local"


REFUSED = {}
for _owner, (_kind, _decls, _name) in _OWNERS.items():
    _skip = len(_decls.splitlines())
    for _binder, (_body, _line, _col) in _binders(_name).items():
        REFUSED[f"{_binder}_over_{_owner}"] = (_decls + _body, _skip + _line, _col, _kind, _name)

# A const declared after the fn that binds its name: tables are whole-module.
REFUSED["let_over_a_later_const"] = (
    "fn main() -> i32\n    let K: i32 = 3\n    0\nconst K: i32 = 7\n", 2, 9, "const", "K")
# A const of any type: none of them leaves the name to the local.
for _what, _ty, _value in (("string", "StrView", '"a"'), ("float", "f64", "1.5"),
                           ("array", "[2]i32", "[1, 2]"), ("bool", "bool", "true")):
    REFUSED[f"let_over_a_{_what}_const"] = (
        f"const K: {_ty} = {_value}\nfn main() -> i32\n    let K: i32 = 3\n    0\n",
        3, 9, "const", "K")
# Each name of a tuple `let` at its own place: here the second.
REFUSED["tuple_let_second_name"] = (
    "const K: i32 = 7\nstruct P\n    a: i32\n    b: i32\nfn p() -> P\n    P { a: 1, b: 2 }\n"
    "fn main() -> i32\n    let (a, K) = p()\n    a\n", 8, 13, "const", "K")
# A name that is two module values is named as the first of const, global, variant.
REFUSED["let_over_a_const_named_like_a_variant"] = (
    "const None: i32 = 3\nfn main() -> i32\n    let None: i32 = 4\n    0\n", 3, 9, "const", "None")
# A payload over a variant of the payload's own enum (§8.2's old "test").
REFUSED["payload_over_its_own_variant"] = (
    "enum C\n    R\n    S\nfn f(o: Option<C>) -> i32\n    match o\n        Some(R) => 1\n"
    "        _ => 2\nfn main() -> i32\n    f(Some(C.S))\n", 6, 14, "variant", "R")
# An integer const on an integer payload: the same, not a compare.
REFUSED["payload_over_an_integer_const"] = (
    "const K: i32 = 7\nfn f(o: Option<i32>) -> i32\n    match o\n        Some(K) => 1\n"
    "        _ => 2\nfn main() -> i32\n    f(Some(5))\n", 4, 14, "const", "K")
# A top-level arm naming a non-integer const: a binding, so refused.
REFUSED["arm_over_a_string_const_on_an_integer"] = (
    'const F: StrView = "a"\nfn f(x: i32) -> i32\n    match x\n        0 => 1\n'
    "        F => 2\nfn main() -> i32\n    f(5)\n", 5, 9, "const", "F")
# Only an integer const compares: a float or bool one would bind.
REFUSED["arm_over_a_float_const_on_an_integer"] = (
    "const F: f64 = 1.5\nfn f(x: i32) -> i32\n    match x\n        0 => 1\n"
    "        F => 2\nfn main() -> i32\n    f(5)\n", 5, 9, "const", "F")
REFUSED["arm_over_a_bool_const_on_a_bool"] = (
    "const T: bool = true\nfn f(b: bool) -> i32\n    match b\n        false => 1\n"
    "        T => 2\nfn main() -> i32\n    f(true)\n", 5, 9, "const", "T")
# A variant of another enum against an integer scrutinee.
REFUSED["arm_over_a_variant_on_an_integer"] = (
    "enum C\n    R\n    S\nfn f(x: i32) -> i32\n    match x\n        0 => 1\n"
    "        R => 2\nfn main() -> i32\n    f(5)\n", 7, 9, "variant", "R")
# Never called: the rule is about names, so it needs no instance.
REFUSED["generic_fn_never_called"] = (
    "const K: i32 = 7\nfn g<T>(x: T) -> i32\n    let K: i32 = 3\n    0\n"
    "fn main() -> i32\n    0\n", 3, 9, "const", "K")


# The one-meaning rule's other half: a call says it wants a fn.
# name -> (source, line, column of the callee)
CALLS_REFUSED = {
    "int_local_named_like_a_fn": (
        "fn k() -> i32\n    7\nfn main() -> i32\n    let k: i32 = 3\n    k()\n", 5, 5),
    "untyped_local_named_like_a_fn": (
        "fn k() -> i32\n    7\nfn main() -> i32\n    let k = 3\n    k()\n", 5, 5),
    "param_named_like_a_fn": (
        "fn k() -> i32\n    7\nfn g(k: i32) -> i32\n    k()\nfn main() -> i32\n    g(3)\n", 4, 5),
    "var_named_like_a_fn": (
        "fn k() -> i32\n    7\nfn main() -> i32\n    var k: i32 = 3\n    k = 4\n    k()\n",
        6, 5),
}


def _call_message(name):
    return f"'{name}' is a local, not a fn: it can't be called"


# name -> (source, exit code): each keeps running, on all three.
KEPT = {
    # A fn's name is free for a local, and the local wins.
    "local_named_like_a_fn": (
        "fn k() -> i32\n    7\nfn main() -> i32\n    let k: i32 = 3\n    k\n", 3),
    "param_named_like_a_fn": (
        "fn k() -> i32\n    7\nfn g(k: i32) -> i32\n    k\nfn main() -> i32\n    g(3)\n", 3),
    "fn_valued_local_calls": (
        "fn a() -> i32\n    5\nfn main() -> i32\n    let k: fn() -> i32 = a\n    k()\n", 5),
    "fn_valued_param_calls": (
        "fn a() -> i32\n    5\nfn g(k: fn() -> i32) -> i32\n    k()\n"
        "fn main() -> i32\n    g(a)\n", 5),
    "the_fn_still_calls_elsewhere": (
        "fn k() -> i32\n    7\nfn g() -> i32\n    let k: i32 = 3\n    k\n"
        "fn main() -> i32\n    k() * 10 + g()\n", 73),
    # A top-level arm naming an integer const against an integer compares (§8.2).
    "arm_const_compares": (
        "const K: i32 = 5\nfn f(x: i32) -> i32\n    match x\n        K => 1\n        _ => 2\n"
        "fn main() -> i32\n    f(5) * 10 + f(4)\n", 12),
    # ...and a variant of the scrutinee's own enum is that variant.
    "arm_variant_is_the_variant": (
        "enum C\n    R\n    S\nfn f(c: C) -> i32\n    match c\n        R => 1\n        S => 2\n"
        "fn main() -> i32\n    f(C.S)\n", 2),
    # A const reads as the const; nothing else holds its name.
    "const_reads_as_itself": ("const K: i32 = 7\nfn main() -> i32\n    K\n", 7),
    "global_reads_as_itself": ("var G: i32 = 7\nfn main() -> i32\n    G = G + 1\n    G\n", 8),
    # Case matters: `k` is no `K`.
    "other_case": ("const K: i32 = 7\nfn main() -> i32\n    let k: i32 = 3\n    k + K\n", 10),
    # A field, a struct or a type param named like one isn't a local.
    "field_named_like_a_const": (
        "const K: i32 = 7\nstruct T\n    K: i32\nfn main() -> i32\n    let t = T { K: 3 }\n"
        "    t.K\n", 3),
    "binder_named_like_a_struct": (
        "struct Q\n    v: i32\nfn main() -> i32\n    let Q: i32 = 3\n    Q\n", 3),
    # `_` binds nothing.
    "wildcard_payload": (
        "const K: i32 = 7\nfn f(o: Option<i32>) -> i32\n    match o\n        Some(_) => 1\n"
        "        _ => 2\nfn main() -> i32\n    f(Some(5))\n", 1),
}


def _write(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    (tmp_path / "pm.ritz").write_text(_MODULE)
    return src, tmp_path / "unit.ll"


def _compile(request, compiler, tmp_path, source):
    src, ll = _write(tmp_path, source)
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
    return proc, ll


def _located(compiler, out, line, col, message):
    """ritz1 says `error:` after the place; ritz0 doesn't."""
    sep = "" if compiler == "ritz0" else "error: "
    return re.findall(rf"unit\.ritz:{line}:{col}: {sep}{re.escape(message)}$", out, re.M)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_local_cant_take_a_module_values_name(request, tmp_path, compiler, name):
    source, line, col, kind, shown = REFUSED[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    message = _message(kind, shown)
    hits = _located(compiler, out, line, col, message)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r} at {line}:{col}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CALLS_REFUSED))
def test_a_local_that_holds_no_fn_cant_be_called(request, tmp_path, compiler, name):
    source, line, col = CALLS_REFUSED[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    hits = _located(compiler, out, line, col, _call_message("k"))
    assert len(hits) == 1, f"{compiler}, {name}: want the call refused at {line}:{col}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(KEPT))
def test_what_the_rule_leaves_alone_still_runs(request, tmp_path, compiler, name):
    source, code = KEPT[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-1500:]}"
    exe = tmp_path / "unit"
    link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link.insert(3, str(RITZ_START))
    subprocess.run(link, check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_binder_is_reported(request, tmp_path, compiler):
    """Two in one fn: both named, on every compiler, so a fix can be done at once."""
    source = ("const K: i32 = 7\nvar G: i32 = 7\nfn main() -> i32\n    let K: i32 = 3\n"
              "    let G: i32 = 4\n    0\n")
    proc, _ = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert _located(compiler, out, 4, 9, _message("const", "K")), out[-1500:]
    assert _located(compiler, out, 5, 9, _message("global", "G")), out[-1500:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_binder_comes_before_match_coverage(request, tmp_path, compiler):
    """The first error agrees: a match that also misses an arm names the binder first."""
    source = ("const K: i32 = 7\nfn f(o: Option<i32>) -> i32\n    match o\n"
              "        Some(K) => 1\nfn main() -> i32\n    f(Some(5))\n")
    proc, _ = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    first = next(line for line in out.splitlines() if "unit.ritz:" in line)
    assert _message("const", "K") in first, out[-1500:]
