"""AGAST #3984: `not g[i].f` / `g[i].f and ..` on a bool field of an element
of a GLOBAL `[N]T` array is a bool, on every compiler.

THE DEFECT

ritz1's bool_check (ritz1/src/bool_check.ritz) types `g[i].f` through
sbk_receiver, which names the struct `g[i]` is.  For a global it answered
`g.type_name`, but a `var g: [N]T` global keeps T in `array_elem_type_name`
(type_name is null), so the field went untyped and `not` / `and` / `or` /
`assert` on it was "must be bool, and ritz1 cannot tell that it is".  A local
`[N]T` worked: its SemaVar carries T as its type_name.  harland's kernel hit it
at cap/table.ritz:76,111 (`var cap_tables: [64]CapTable`).

THE FIX

sbk_receiver names a global array's element struct, as it already did for a
const array.

Every row runs on ritz0, ritz1 and ritz1_selfhosted, over a global and a local
array (of a struct, and of bool: #3977, folded in), and reads the element both
ways (a true and a false one), so a check that passes but lowers the wrong
value still fails.
"""

import pytest

from test_ref_into_value import COMPILERS, _ids, _run

# The ticket's minimal repro, verbatim.
TICKET_REPRO = """\
struct T
    in_use: bool
    pid: u32

var ts: [4]T

pub fn main() -> i32
    var i: i32 = 0
    if not ts[i].in_use
        if ts[i].in_use and ts[i].pid == 0
            return 1
        return 7
    return 0
"""

# Each body runs with ts[0] = {false, 0} and ts[1] = {true, 5}; 7 is a pass.
BODIES = {
    "not": """\
    if not ts[i].in_use
        if not ts[i + 1].in_use
            return 2
        return 7
    return 1
""",
    "and": """\
    if ts[i + 1].in_use and ts[i + 1].pid == 5
        if ts[i].in_use and ts[i].pid == 0
            return 2
        return 7
    return 1
""",
    "or": """\
    if ts[i].in_use or ts[i + 1].in_use
        if ts[i].in_use or ts[i].pid == 9
            return 2
        return 7
    return 1
""",
    "if": """\
    if ts[i].in_use
        return 2
    if ts[i + 1].in_use
        return 7
    return 1
""",
    "assert": """\
    assert ts[i + 1].in_use
    assert not ts[i].in_use
    assert ts[i + 1].in_use and ts[i + 1].pid == 5
    assert ts[i].in_use or ts[i + 1].in_use
    return 7
""",
}

STORAGE = ["global", "local"]


def _program(storage, form):
    """The body runs in `main`, except `assert`, which is refused there: it
    runs in a [[test_helper]] that `main` returns."""
    glob = "var ts: [4]T\n" if storage == "global" else ""
    local = "    var ts: [4]T\n" if storage == "local" else ""
    fn = "pub fn main() -> i32"
    tail = ""
    if form == "assert":
        fn = "[[test_helper]]\nfn check() -> i32"
        tail = "\npub fn main() -> i32\n    check()\n"
    return f"""\
struct T
    in_use: bool
    pid: u32

{glob}
{fn}
{local}    var i: i32 = 0
    ts[0].in_use = false
    ts[0].pid = 0
    ts[1].in_use = true
    ts[1].pid = 5
{BODIES[form]}{tail}"""


# AGAST #3977 (folded in): a bare `g[i]` of a `[N]bool`, not only a field
# of an `[N]S`.  bs[0] is false, bs[1] true.
BOOL_ARRAY_BODY = """\
    if bs[i]
        return 2
    if not bs[i + 1]
        return 3
    if bs[i] and bs[i + 1]
        return 4
    if not (bs[i] or bs[i + 1])
        return 5
    return 7
"""


def _bool_array_program(storage):
    glob = "var bs: [4]bool\n" if storage == "global" else ""
    local = "    var bs: [4]bool\n" if storage == "local" else ""
    return f"""\
{glob}
pub fn main() -> i32
{local}    var i: i32 = 0
    bs[0] = false
    bs[1] = true
{BOOL_ARRAY_BODY}"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("storage", STORAGE)
def test_bool_array_elem(tmp_path, compiler, storage):
    assert _run(compiler, tmp_path, f"bools_{storage}", _bool_array_program(storage)) == 7


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_ticket_repro(tmp_path, compiler):
    assert _run(compiler, tmp_path, "repro", TICKET_REPRO) == 7


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("storage", STORAGE)
@pytest.mark.parametrize("form", _ids(BODIES))
def test_bool_field_of_array_elem(tmp_path, compiler, storage, form):
    assert _run(compiler, tmp_path, f"{storage}_{form}", _program(storage, form)) == 7
