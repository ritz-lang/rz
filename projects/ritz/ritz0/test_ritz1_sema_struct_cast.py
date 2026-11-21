"""AGAST #4000: ritz1 refuses `as` between two structs on Sema (LARB R72).

THE CHANGE

`as` between two different struct types, by value or through a reference, is
a located error at the `as` (LANGUAGE_SPEC §7.5, LARB R72):

    cannot cast `C` to `D`: `as` doesn't convert between structs: build a `D`
    from the fields

ritz0 refused it in its emitter (#3012).  ritz1 lowered the cast instead:
by value it stored C into D's slot, through a reference it bound D to the
pointer, and clang then refused the IR.  The rule is a check, so it runs on
Sema (struct_cast.ritz), before emission, and the emitter only lowers.

What R72 leaves legal must stay accepted: `r as C` with `r` an `@C` / `@&C`
/ `*C` reads a copy of the referent (§13, #3004), and `@c as *D` is a
pointer cast.

THE TESTS

- Each refused shape stops the compile with no `.ll` emitted, at the `as`,
  in ritz0's words, on both ritz1 binaries.
- The shapes R72 leaves alone still compile.
- A source pin: the refusal is in struct_cast.ritz and sema_walk calls it;
  no emitter module carries the words.
"""

import re
from pathlib import Path

import pytest

from test_ref_into_value import _compile

RITZ_ROOT = Path(__file__).resolve().parent.parent
SRC = RITZ_ROOT / "ritz1" / "src"
COMPILERS = ["ritz1", "ritz1_selfhosted"]
_FOUND = r"main\.ritz:(\d+:\d+): (?:error: )?(.*)"

ERROR = ("cannot cast `C` to `D`: `as` doesn't convert between structs: "
         "build a `D` from the fields")

HEAD = """\
struct C
    x: i32

struct D
    x: i32
"""

# `^` marks the `as` the error lands on.  One row per shape ritz0 refuses:
# by value, and through an `@` and a `*` (its `@` and `*` take one path).
REFUSED = {
    "by_value": (HEAD + "fn f(c: C) -> i32\n    let d: D = c ^as D\n    d.x\n"
                 "\npub fn main() -> i32\n    let c = C { x: 4 }\n    f(c)\n", ERROR),
    "shared": (HEAD + "fn f(r: @C) -> i32\n    let d: D = r ^as D\n    d.x\n"
               "\npub fn main() -> i32\n    var c = C { x: 4 }\n    f(@c)\n", ERROR),
    "pointer": (HEAD + "fn f(r: *C) -> i32\n    let d: D = r ^as D\n    d.x\n"
                "\npub fn main() -> i32\n    var c = C { x: 4 }\n    f(@c)\n", ERROR),
}

# Accepted: `r as C` reads the referent (#3004), `@c as *D` is a pointer
# cast, and a pointer stays a pointer.
OPEN = {
    "shared_to_the_same_struct": HEAD + "fn f(r: @C) -> i32\n    let d: C = r as C\n    d.x\n",
    "mutable_to_the_same_struct": HEAD + "fn f(r: @&C) -> i32\n    let d: C = r as C\n    d.x\n",
    "pointer_to_the_same_struct": HEAD + "fn f(r: *C) -> i32\n    let d: C = r as C\n    d.x\n",
    "address_as_another_pointer": HEAD + "fn f(r: *D) -> i32\n    r.x\n\n"
                                  "pub fn main() -> i32\n    var c = C { x: 4 }\n    f(@c as *D)\n",
    "pointer_retyped": HEAD + "fn f(p: *C) -> *D\n    p as *D\n",
}

TAIL = "\npub fn main() -> i32\n    0\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(REFUSED))
def test_a_struct_cast_is_refused_before_emission(request, tmp_path, compiler, site):
    request.getfixturevalue("ritz1_bin")
    marked, words = REFUSED[site]
    at = marked[:marked.index("^")]
    at = f"{at.count(chr(10)) + 1}:{len(at) - at.rfind(chr(10))}"
    src = marked.replace("^", "", 1)
    comp, ll, _ = _compile(compiler, tmp_path, f"struct_cast_{site}", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {site}:\n{src}"
    assert not ll.exists(), f"{compiler} emitted IR for {site} before refusing:\n{out[-2000:]}"
    assert re.findall(_FOUND, out) == [(at, words)], (
        f"{compiler}: {site} wanted {at}: {words}, got:\n{out[-2000:]}")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(OPEN))
def test_what_r72_leaves_legal_still_compiles(request, tmp_path, compiler, site):
    request.getfixturevalue("ritz1_bin")
    src = OPEN[site]
    if "pub fn main" not in src:
        src += TAIL
    comp, ll, _ = _compile(compiler, tmp_path, f"struct_cast_open_{site}", src)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} refused a legal cast ({site}):\n{src}\n{(comp.stdout + comp.stderr)[-2000:]}")


@pytest.mark.unit
def test_the_refusal_is_on_sema_not_the_emitter():
    sema = (SRC / "struct_cast.ritz")
    assert sema.exists(), "no struct_cast.ritz: the rule isn't on Sema"
    assert "doesn't convert between structs" in sema.read_text()
    assert "struct_cast_check" in (SRC / "sema_walk.ritz").read_text(), (
        "sema_walk doesn't call struct_cast_check")
    for path in SRC.glob("emitter*.ritz"):
        assert "doesn't convert between structs" not in path.read_text(), (
            f"{path.name} still carries the struct-to-struct refusal; it belongs to Sema")
