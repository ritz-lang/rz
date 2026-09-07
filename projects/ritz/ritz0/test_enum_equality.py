#!/usr/bin/env python3
"""`==`/`!=` on a payload-less enum must compare tags and emit valid IR.

docs/STYLE.md:1131 documents this as THE idiom, in prose contrasting it with
`match`:

    match arms name the variant bare (`Ident =>`), while an equality test
    must qualify it (`token.kind == TokenKind.Ident`)

It has never worked. Two successive wrongs:

  main @ f336bae   accepted it and emitted

                       icmp eq %"enum.mod.TokenKind" %a, %b

                   `icmp` takes integers/pointers only, so this is invalid
                   IR. `make check-doc-examples` compiles to .ll and never
                   links, so the doc block passed; any real build died at
                   clang with "icmp requires integer operands" pointing at
                   generated IR.

  c5cc145 (#1321)  added `_reject_aggregate_compare` to stop `StrView ==
                   StrView` producing that same red herring. Enums are
                   struct-typed too, so the guard caught them as collateral
                   and turned the doc block into a hard build failure —
                   bootstrap/"Documentation examples compile" red on main.

The rejection was the right instinct aimed one notch too wide. An enum's
layout is `{ i8 tag, [pad], [payload] }`, so for an enum whose variants ALL
carry no payload the tag alone is the whole value and comparing it is exact.

A payload-carrying enum must STAY rejected: tag-only equality would make
`Some(1) == Some(2)` true, which is a wrong answer rather than a refusal.
"""

import subprocess
import sys
from pathlib import Path

RITZ0 = Path(__file__).resolve().parent / "ritz0.py"


def _compile(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
        capture_output=True,
        text=True,
    )


def _verify_ir(tmp_path):
    """Parse the emitted IR. This is what the .ll-only doc gate never did."""
    return subprocess.run(
        [sys.executable, "-c",
         "import sys; import llvmlite.binding as llvm; "
         "llvm.parse_assembly(open(sys.argv[1]).read())",
         str(tmp_path / "unit.ll")],
        capture_output=True, text=True)


# Verbatim shape of the docs/STYLE.md:1131 block that took bootstrap red.
FIELDLESS_ENUM_EQ = """\
enum TokenKind
    Ident
    Number


struct Token
    kind: TokenKind


fn handle_ident(t: Token) -> i32
    1

fn unexpected_token() -> i32
    -1


fn dispatch_chained(token: Token) -> i32
    if token.kind == TokenKind.Ident
        return handle_ident(token)
    else
        return unexpected_token()
"""


def test_fieldless_enum_equality_emits_valid_ir(tmp_path):
    result = _compile(tmp_path, FIELDLESS_ENUM_EQ)
    assert result.returncode == 0, (
        "the documented `token.kind == TokenKind.Ident` idiom was rejected:\n"
        + result.stderr
    )
    verify = _verify_ir(tmp_path)
    assert verify.returncode == 0, (
        "enum `==` emitted IR that does not parse — the f336bae `icmp` on a "
        f"struct operand is back:\n{verify.stderr}"
    )


FIELDLESS_ENUM_NE = """\
enum Colour
    Red
    Green
    Blue


fn differs(a: Colour, b: Colour) -> i32
    if a != b
        return 1
    return 0
"""


def test_fieldless_enum_inequality_emits_valid_ir(tmp_path):
    result = _compile(tmp_path, FIELDLESS_ENUM_NE)
    assert result.returncode == 0, f"enum `!=` rejected:\n{result.stderr}"
    verify = _verify_ir(tmp_path)
    assert verify.returncode == 0, f"invalid IR for enum `!=`: {verify.stderr}"


# The comparison must be a real tag test, not a constant. A guard that always
# answered "equal" would satisfy the two tests above.
DISCRIMINATING_EQ = """\
enum Colour
    Red
    Green
    Blue


fn main() -> i32
    let a: Colour = Colour.Red
    let b: Colour = Colour.Blue
    var score: i32 = 0
    if a == a
        score += 1
    if a == b
        score += 10
    if a != b
        score += 100
    return score
"""


def test_enum_equality_discriminates(tmp_path):
    """Red == Red, Red != Blue. Expect 1 + 100; 10 would mean always-equal."""
    src = tmp_path / "disc.ritz"
    src.write_text(DISCRIMINATING_EQ)
    compiled = subprocess.run(
        [sys.executable, str(RITZ0), str(src), "-o", str(tmp_path / "disc.ll")],
        capture_output=True, text=True)
    assert compiled.returncode == 0, compiled.stderr

    exe = tmp_path / "disc"
    # -nostdlib matches build.py: ritz0 emits its own `_start` and makes raw
    # syscalls, so linking against crt1.o would double-define the entry point.
    link = subprocess.run(
        ["clang", str(tmp_path / "disc.ll"), "-o", str(exe), "-nostdlib"],
        capture_output=True, text=True)
    assert link.returncode == 0, (
        f"enum `==` produced IR clang rejects:\n{link.stderr}")

    run = subprocess.run([str(exe)], capture_output=True)
    assert run.returncode == 101, (
        f"expected 101 (1 self-equal + 100 differs), got {run.returncode}; "
        "10 would mean the comparison always reports equal"
    )


# A payload-carrying enum must stay rejected: comparing tags alone would make
# Some(1) == Some(2) true. Refusing is correct; answering wrongly is not.
PAYLOAD_ENUM_EQ = """\
enum Shape
    A(i64)
    B(i64)


fn same(x: Shape, y: Shape) -> i32
    if x == y
        return 1
    return 0
"""


def test_payload_enum_equality_is_rejected(tmp_path):
    result = _compile(tmp_path, PAYLOAD_ENUM_EQ)
    assert result.returncode != 0, (
        "`==` on a payload-carrying enum compiled — tag-only equality would "
        "report Some(1) == Some(2) as true.\nstdout:\n" + result.stdout
    )


STRVIEW_EQ = """\
fn main() -> i32
    let a: StrView = "x"
    let b: StrView = "y"
    if a == b
        return 1
    return 0
"""


def test_strview_equality_still_rejected(tmp_path):
    """The guard #1321 added must survive this narrowing."""
    result = _compile(tmp_path, STRVIEW_EQ)
    assert result.returncode != 0, (
        "`StrView == StrView` compiled again — narrowing the aggregate-compare "
        "guard to exempt enums must not exempt every struct."
    )
    assert "strview_eq" in (result.stdout + result.stderr), (
        "the StrView rejection lost its remediation hint"
    )
