"""AGAST #3740: a `pass` arm gives a typed struct / enum `let` / `var` no value.

LANGUAGE_SPEC §8: `pass` is the body of an arm that does nothing, so it has no
value.  `var c: Big = match t` with `A => *p` and `B => pass` has nothing to
put in `c` when `t` is `B`.  ritz0 refused it, at the declaration:

    `c` is declared `Big` but its initialiser has no single value type: its
    match / if arms yield values that cannot be merged at that type

ritz1 and ritz1_selfhosted compiled it (rc 0), the `pass` arm's incoming a
`zeroinitializer` of %Big: a silent all-zero `c`.  Now all three refuse it,
in ritz0's words, at the `let` / `var` (ritz1 puts `error: ` before the
message, as diag.ritz does), and write no IR.

Pinned here: a named struct (any size: #3696 sends a large one through a result
slot, a small one through a phi), a generic's instance, a user enum, `let` and
`var`, the `pass` arm first, last, or as a block.  ritz0 refuses a pointer, `Option`, untyped,
`return`ed or assigned one too, but misnames the type or crashes unlocated
(AGAST #3758). The `if` form and a scalar slot's `pass` arm, a silent 0, wait
on a decision (#3759).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

BIG = "struct Big\n    a: i64\n    b: i64\n    c: i64\n    d: i64\n\n"
SMALL = "struct Big\n    a: i64\n    b: i64\n\n"
ENUM_T = "enum T\n    A\n    B\n\n"


def _struct_form(struct, decl, arm_a, arm_b, init):
    return (
        f"{struct}{ENUM_T}fn f(t: T, p: *Big) -> i64\n"
        f"    {decl} c: Big = match t\n"
        f"        T.A => {arm_a}\n"
        f"        T.B => {arm_b}\n"
        "    return c.a\n\n"
        "fn main() -> i32\n"
        f"    var b = Big {{ {init} }}\n"
        "    return f(T.A, @b) as i32\n"
    )


BIG_INIT = "a: 1, b: 2, c: 3, d: 4"
# The `var` / `let` sits on line 12 (10 for the small struct), column 5.
# name -> (source, line, col, declared type)
FORMS = {
    # The ticket's repro: a large struct, `pass` last.
    "var_large": (_struct_form(BIG, "var", "*p", "pass", BIG_INIT), 12, 5, "Big"),
    "let_large": (_struct_form(BIG, "let", "*p", "pass", BIG_INIT), 12, 5, "Big"),
    "pass_first": (_struct_form(BIG, "var", "pass", "*p", BIG_INIT), 12, 5, "Big"),
    "pass_block": (
        _struct_form(BIG, "var", "*p", "\n            pass", BIG_INIT),
        12,
        5,
        "Big",
    ),
    # Two words: merged through a phi, not #3696's result slot.
    "var_small": (_struct_form(SMALL, "var", "*p", "pass", "a: 1, b: 2"), 10, 5, "Big"),
    "var_enum": (
        (
            f"{ENUM_T}fn f(t: T) -> i64\n"
            "    var c: T = match t\n"
            "        T.A => T.B\n"
            "        T.B => pass\n"
            "    return 0\n\n"
            "fn main() -> i32\n"
            "    return f(T.A) as i32\n"
        ),
        6,
        5,
        "T",
    ),
    # A generic's instance is named as both compilers mangle it.
    "var_generic": (
        (
            "struct Box<T>\n    v: T\n\n"
            "fn f(n: i64) -> i64\n"
            "    var c: Box<i64> = match n\n"
            "        0 => Box<i64> { v: 3 }\n"
            "        _ => pass\n"
            "    return c.v\n\n"
            "fn main() -> i32\n"
            "    return f(0) as i32\n"
        ),
        5,
        5,
        "Box$i64",
    ),
}


def _message(declared):
    return (
        f"`c` is declared `{declared}` but its initialiser has no single value "
        "type: its match / if arms yield values that cannot be merged at that type"
    )


def _compile(compiler, tmp_path, source):
    src = tmp_path / "bad.ritz"
    src.write_text(source)
    ll = tmp_path / "bad.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run(
        [str(binary), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _assert_refused(compiler, tmp_path, name):
    source, line, col, declared = FORMS[name]
    message = _message(declared)
    proc = _compile(compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, out
    hits = re.findall(
        rf"bad\.ritz:{line}:{col}: (?:error: )?{re.escape(message)}$", out, re.MULTILINE
    )
    assert len(hits) == 1, out
    assert out.count("no single value type") == 1, out
    assert not (tmp_path / "bad.ll").exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("name", FORMS)
def test_ritz0_refuses_pass_arm_value(tmp_path, name):
    _assert_refused("ritz0", tmp_path, name)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("name", FORMS)
def test_ritz1_refuses_pass_arm_value(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    _assert_refused(compiler, tmp_path, name)


# The same match as a statement, or with every arm a value, still compiles
# on all three: the refusal is the `pass` arm's missing value, nothing else.
ACCEPTED = {
    "statement": (
        f"{BIG}{ENUM_T}fn f(t: T, p: *Big) -> i64\n"
        "    var c: Big = *p\n"
        "    match t\n"
        "        T.A => c = *p\n"
        "        T.B => pass\n"
        "    return c.a\n\n"
        "fn main() -> i32\n"
        f"    var b = Big {{ {BIG_INIT} }}\n"
        "    return f(T.A, @b) as i32\n"
    ),
    "all_values": _struct_form(BIG, "var", "*p", "*p", BIG_INIT),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("name", ACCEPTED)
def test_value_arms_still_compile(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    proc = _compile(compiler, tmp_path, ACCEPTED[name])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (tmp_path / "bad.ll").exists()
