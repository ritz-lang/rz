"""Named struct-variant patterns and construction (AGAST #4187).

docs/ENUM_VARIANTS.md §4–5 specify both named forms of a struct-declared
variant:

    match msg
        ConsoleLog { level, message } => ...     # named pattern
    let b = SetViewport { width: 640, height: 480 }  # named construction

but no compiler implemented them: ritz0 refused the pattern ("Expected
FATARROW, got LBRACE") and the literal ("unknown type `SetViewport`"), and
ritz1 refused both the same way (#3993).

The rule, on all three compilers: each field is named exactly once, in any
order; the names map to the variant's field positions, so a named pattern
binds exactly what the positional pattern binds, and a named literal builds
exactly what the positional constructor builds.  Qualified patterns
(`Msg.SetViewport { .. } =>`) and literals (`Msg.SetViewport { width: 1,
height: 2 }`, AGAST #4275) follow the same rules.  A named form on a
variant declared without field names, an unknown field, a repeated one or a
missing one is refused at the variant's name.
"""

import re

import pytest
from test_ref_into_value import COMPILERS, _assert_refused, _compile, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

ENUM = (
    "enum Msg\n"
    "    Stop\n"
    "    Reload(i32)\n"
    "    SetViewport\n"
    "        width: i32\n"
    "        height: i32\n"
    "    Mixed\n"
    "        a: u8\n"
    "        b: i64\n"
    "        c: i32\n"
    "\n"
)

# Each program exits 3 on success.
RUNS = {
    # §5: named construction, written in field order, matched positionally.
    "build_in_order": ENUM
    + "pub fn main() -> i32\n"
    "    let m = SetViewport { width: 640, height: 480 }\n"
    "    match m\n"
    "        SetViewport(w, h) => if w == 640 and h == 480 then 3 else 1\n"
    "        _ => 2\n",
    # Any order: the literal is reordered into field order.
    "build_any_order": ENUM
    + "pub fn main() -> i32\n"
    "    let m = SetViewport { height: 480, width: 640 }\n"
    "    match m\n"
    "        SetViewport(w, h) => if w == 640 and h == 480 then 3 else 1\n"
    "        _ => 2\n",
    # §4: named pattern, any order, binds by name.
    "pattern_any_order": ENUM
    + "pub fn main() -> i32\n"
    "    let m = SetViewport(640, 480)\n"
    "    match m\n"
    "        SetViewport { height, width } => if width == 640 and height == 480 then 3 else 1\n"
    "        _ => 2\n",
    # Qualified pattern.
    "pattern_qualified": ENUM
    + "pub fn main() -> i32\n"
    "    let m = Msg.SetViewport(640, 480)\n"
    "    match m\n"
    "        Msg.SetViewport { width, height } => if width == 640 and height == 480 then 3 else 1\n"
    "        _ => 2\n",
    # Fields of mixed widths, out of order both ways: every field lands at
    # its own offset.
    "mixed_widths": ENUM
    + "pub fn main() -> i32\n"
    "    let m = Mixed { c: 7, a: 200, b: 5000000000 }\n"
    "    match m\n"
    "        Mixed { b, c, a } => if a == 200 and b == 5000000000 and c == 7 then 3 else 1\n"
    "        _ => 2\n",
    # #3993's program: a named literal as an argument and under an annotation.
    "struct_lit_variant": "enum Msg\n    Log\n        level: i32\n    Stop\n\n"
    "fn g(m: Msg) -> i32\n"
    "    match m\n"
    "        Log { level } => level - 1\n"
    "        Stop => 0\n\n"
    "pub fn main() -> i32\n"
    "    let a: Msg = Log { level: 4 }\n"
    "    g(a)\n",
    "arg": "enum Msg\n    Log\n        level: i32\n    Stop\n\n"
    "fn g(m: Msg) -> i32\n"
    "    match m\n"
    "        Log(l) => l\n"
    "        Stop => 0\n\n"
    "pub fn main() -> i32\n"
    "    g(Log { level: 3 })\n",
    # A block-bodied arm and a statement-position match.
    # Qualified construction (AGAST #4275), any order: `Msg.SetViewport { .. }`
    # is `Msg.SetViewport(640, 480)`.
    "build_qualified": ENUM
    + "pub fn main() -> i32\n"
    "    let m = Msg.SetViewport { height: 480, width: 640 }\n"
    "    match m\n"
    "        Msg.SetViewport { width, height } => if width == 640 and height == 480 then 3 else 1\n"
    "        _ => 2\n",
    # Qualified, as an argument, across lines, with a trailing comma.
    "build_qualified_arg": ENUM
    + "fn g(m: Msg) -> i32\n"
    "    match m\n"
    "        Mixed(a, b, c) => (a as i32) + (b as i32) - c\n"
    "        _ => 0\n\n"
    "pub fn main() -> i32\n"
    "    g(Msg.Mixed {\n"
    "        c: 4,\n"
    "        b: 5,\n"
    "        a: 2,\n"
    "    })\n",
    # A qualified literal as a match scrutinee, and a field access as an
    # `if`/`while` condition: neither swallows the block that follows.
    "qualified_scrutinee_and_conditions": ENUM
    + "struct P\n"
    "    ok: bool\n\n"
    "pub fn main() -> i32\n"
    "    let p = P { ok: true }\n"
    "    var r: i32 = 0\n"
    "    if p.ok\n"
    "        r = 1\n"
    "    while p.ok and r < 2\n"
    "        r = r + 1\n"
    "    match Msg.SetViewport { width: 1, height: 0 }\n"
    "        SetViewport(w, h) =>\n"
    "            r = r + w - h\n"
    "        _ => r = 9\n"
    "    r\n",
    "block_arm": ENUM
    + "pub fn main() -> i32\n"
    "    var r: i32 = 0\n"
    "    match Mixed { a: 1, b: 1, c: 1 }\n"
    "        Mixed { a, b, c } =>\n"
    "            r = (a as i32) + (b as i32) + c\n"
    "        _ => r = 9\n"
    "    r\n",
}


@pytest.mark.parametrize("compiler,name", [(c, n) for c in COMPILERS for n in sorted(RUNS)])
def test_named_forms_run(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, RUNS[name]) == 3


MAIN = "\npub fn main() -> i32\n    3\n"

# `^` marks where the error lands: on the variant's name.
REFUSED = {
    # Patterns.
    "pat_missing": (
        "fn f(m: Msg) -> i32\n    match m\n        ^SetViewport { width } => width\n        _ => 0\n",
        "missing field `height` of variant `SetViewport`",
    ),
    "pat_unknown": (
        "fn f(m: Msg) -> i32\n    match m\n        ^SetViewport { width, depth } => width\n        _ => 0\n",
        "variant `SetViewport` has no field `depth`",
    ),
    "pat_twice": (
        "fn f(m: Msg) -> i32\n    match m\n        ^SetViewport { width, width } => width\n        _ => 0\n",
        "field `width` of variant `SetViewport` named twice",
    ),
    "pat_tuple_variant": (
        "fn f(m: Msg) -> i32\n    match m\n        ^Reload { x } => x\n        _ => 0\n",
        "variant `Reload` has no named fields",
    ),
    # Construction.
    "lit_missing": (
        "fn f() -> Msg\n    ^SetViewport { width: 1 }\n",
        "missing field `height` of variant `SetViewport`",
    ),
    "lit_unknown": (
        "fn f() -> Msg\n    ^SetViewport { width: 1, height: 2, depth: 3 }\n",
        "variant `SetViewport` has no field `depth`",
    ),
    "lit_twice": (
        "fn f() -> Msg\n    ^SetViewport { width: 1, width: 2 }\n",
        "field `width` of variant `SetViewport` named twice",
    ),
    "lit_tuple_variant": (
        "fn f() -> Msg\n    ^Reload { x: 1 }\n",
        "variant `Reload` has no named fields",
    ),
    # Qualified construction (AGAST #4275): located where the form begins.
    "qlit_missing": (
        "fn f() -> Msg\n    ^Msg.SetViewport { width: 1 }\n",
        "missing field `height` of variant `SetViewport`",
    ),
    "qlit_unknown": (
        "fn f() -> Msg\n    ^Msg.SetViewport { width: 1, height: 2, depth: 3 }\n",
        "variant `SetViewport` has no field `depth`",
    ),
    "qlit_twice": (
        "fn f() -> Msg\n    ^Msg.SetViewport { width: 1, width: 2 }\n",
        "field `width` of variant `SetViewport` named twice",
    ),
    "qlit_tuple_variant": (
        "fn f() -> Msg\n    ^Msg.Reload { x: 1 }\n",
        "variant `Reload` has no named fields",
    ),
}


@pytest.mark.parametrize("compiler,site", [(c, s) for c in COMPILERS for s in sorted(REFUSED)])
def test_named_forms_refused(tmp_path, compiler, site):
    marked, message = REFUSED[site]
    _assert_refused(compiler, tmp_path, site, ENUM + marked + MAIN, message)


# AGAST #4923: the parser tries a form more than once as it backtracks and
# notes it on each try; ritz1 keys the forms it has reported by the SrcPos of
# the variant's name, so each refused form is reported once, as ritz0 does.
ONCE = (
    ENUM
    + "fn f(m: Msg) -> i32\n    match m\n        SetViewport { depth } => 1\n        _ => 0\n\n"
    + "fn g() -> Msg\n    SetViewport { depth: 3 }\n"
    + MAIN
)


# One case over the compilers, not one each: the suite's test count is capped.
def test_each_refused_form_is_reported_once(tmp_path):
    for compiler in COMPILERS:
        comp, ll, _ = _compile(compiler, tmp_path, "once", ONCE)
        out = comp.stdout + comp.stderr
        assert comp.returncode != 0, f"{compiler} accepted:\n{ONCE}"
        found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?variant `SetViewport` has no field `depth`", out)
        assert sorted(found) == ["14:9", "18:5"], f"{compiler}:\n{out[-2000:]}"
