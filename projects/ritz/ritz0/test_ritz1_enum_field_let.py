"""Regression tests for AGAST #1660: unit-enum values read from struct fields,
bound with an un-annotated `let`, and compared with `==` / `!=` under ritz1.

ritz1 holds a unit (fieldless) enum value as its `%Enum = type { i8 }`
aggregate: the qualified-variant ctor (`Kind.A`), an enum-typed parameter,
`let a = Kind.A` and a struct-field load all produce a `%Kind` register.
ritzlib/argspec.ritz:214 (77_args) broke that model three ways:

    fn eprint_arg_error_message(e: @ArgError)
        let k = e.kind                  # slot stayed i64: `store i64 %<%Kind>`
        if k == ArgErrorKind.UnknownOption
                                        # `icmp eq i64 %<%Kind>, %<%Kind>`

and an enum named only by a struct field never got its `{ i8 }` type decl
("base element of getelementptr must be sized").  The fix keeps the `%Enum`
representation: a `let` from an enum-typed field gets an `%Enum` slot, and
`==` / `!=` with an enum operand compares the extracted i8 tags.

Each program returns 42 when correct and a distinct small code naming the
check that failed otherwise.  ritz0 is the oracle; everything runs at
RUNTIME, and every comparison is exercised with both outcomes so a constant
or inverted lowering cannot pass.
"""

import pytest

from test_ritz1_bool_fields import EXPECTED, _run, ritz1_bin  # noqa: F401, F811

PROGRAMS = {
    # The ticket repro (argspec shape): `let k = e.kind` through a reference
    # param, then an else-if chain.  `arg_kind` names Kind in a signature, as
    # argspec's `arg_error(kind: ArgErrorKind, ..)` does.
    "ticket_repro": """\
enum Kind
    A
    B
    C

struct Err
    kind: Kind
    n: i32

fn make(kind: Kind, n: i32) -> Err
    Err { kind: kind, n: n }

fn classify(e: @Err) -> i32
    let k = e.kind
    if k == Kind.A
        return 1
    else if k == Kind.B
        return 2
    else if k == Kind.C
        return 3
    return 9

pub fn main() -> i32
    let a = make(Kind.A, 1)
    let b = make(Kind.B, 2)
    let c = make(Kind.C, 3)
    if classify(@a) != 1
        return 1
    if classify(@b) != 2
        return 2
    if classify(@c) != 3
        return 3
    return 42
""",
    # The enum is named ONLY by a struct field: it still needs a type decl.
    "field_only_enum": """\
enum Kind
    A
    B
    C

struct Err
    kind: Kind
    n: i32

fn classify(e: @Err) -> i32
    let k = e.kind
    if k == Kind.A
        return 1
    else if k == Kind.B
        return 2
    else
        return 3

pub fn main() -> i32
    let a = Err { kind: Kind.A, n: 1 }
    let b = Err { kind: Kind.B, n: 2 }
    let c = Err { kind: Kind.C, n: 3 }
    if classify(@a) != 1
        return 1
    if classify(@b) != 2
        return 2
    if classify(@c) != 3
        return 3
    return 42
""",
    # Direct field compares (no let), `!=`, compare used as a value, a
    # by-value struct local, a raw pointer and a nested member chain.
    "field_compare_forms": """\
enum Kind
    A
    B
    C

struct Err
    n: i32
    kind: Kind

struct Outer
    tag: i64
    err: Err

fn kind_of(k: Kind) -> Kind
    k

pub fn main() -> i32
    let b = Err { n: 2, kind: kind_of(Kind.B) }
    if b.kind == Kind.A
        return 1
    if b.kind != Kind.B
        return 2
    let is_b = b.kind == Kind.B
    let is_c: bool = b.kind == Kind.C
    if not is_b
        return 3
    if is_c
        return 4
    let k = b.kind
    if k != Kind.B
        return 5
    let p: *Err = @b
    let pk = p.kind
    if pk == Kind.C
        return 6
    if p.kind != Kind.B
        return 7
    let inner = Err { n: 3, kind: Kind.C }
    let o = Outer { tag: 7, err: inner }
    let ok = o.err.kind
    if ok != Kind.C
        return 8
    if o.err.kind == Kind.A
        return 9
    if o.tag != 7
        return 10
    return 42
""",
    # Enum-vs-enum compares between locals, params and fields, both outcomes.
    "enum_vs_enum": """\
enum Kind
    A
    B
    C

struct Err
    kind: Kind
    n: i32

fn same(x: Kind, y: Kind) -> bool
    x == y

fn differ(x: Kind, y: Kind) -> i32
    if x != y
        return 1
    return 0

pub fn main() -> i32
    let a = Kind.A
    let c = Kind.C
    if a == c
        return 1
    if not (a != c)
        return 2
    if not same(Kind.B, Kind.B)
        return 3
    if same(Kind.A, Kind.B)
        return 4
    if differ(Kind.C, Kind.C) != 0
        return 5
    if differ(Kind.C, Kind.A) != 1
        return 6
    let e = Err { kind: Kind.C, n: 1 }
    let k = e.kind
    if k != c
        return 7
    if e.kind == a
        return 8
    if c != e.kind
        return 9
    return 42
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_enum_field_let(ritz1_bin, tmp_path, name):  # noqa: F811
    """ritz1 stored/compared %Enum values as i64 (#1660)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
