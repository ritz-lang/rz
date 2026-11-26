"""AGAST #4836: `(*d).data[a..b]`, a Vec field reached through an explicit
deref of a pointer, slices as `d.data[a..b]` does (R9 rule 2: through a
pointer, `p.f` and `(*p).f` are the same place).

ritz0 compiled it; ritz1 and ritz1_selfhosted refused it: "this can't be
sliced (only String, Vec and Span can)".  resolve_member_field had no arm for
a deref on the left, so the field was never found to be a Vec.  The goliath
workaround (test_block_store.ritz) wrote `d.data[a..b]`.

Each row folds the bytes it sees into its exit code: a view at the wrong
offset, a wrong length or a copy that aliased shows.
"""

import pytest

import test_table_rows as table_rows
from test_table_rows import ALL, Row, Run

pytestmark = pytest.mark.integration

HEAD = """\
import ritzlib.gvec
import ritzlib.span

struct Disk
    data: Vec<u8>

struct H
    n: i64

impl H
    pub fn rec(self: @H, a: [u8]) -> i64
        10 * a.len + (a[a.len - 1] as i64)

fn take(a: [u8]) -> i64
    10 * a.len + (a[a.len - 1] as i64)

fn disk() -> Disk
    var v: Vec<u8> = vec_new<u8>()
    v.push(1)
    v.push(7)
    v.push(3)
    Disk { data: v }
"""

# name -> (the fn under test, the call main makes, expected exit status)
FORMS = {
    # The ticket's repro: a Span let, through a `*Disk`.
    "let_span_ptr": ("""\
fn go(d: *Disk) -> i64
    let s: [u8] = (*d).data[0..2]
    s[1] as i64
""", "go(@&d)", 7),
    # Through an `@Disk` reference.
    "let_span_ref": ("""\
fn go(d: @Disk) -> i64
    let s: [u8] = (*d).data[1..3]
    (s.len * 10) as i64 + s[1] as i64
""", "go(@d)", 23),
    # A free fn's `[u8]` argument.
    "free_fn_arg": ("""\
fn go(d: *Disk) -> i64
    take((*d).data[0..2])
""", "go(@&d)", 27),
    # A method's `[u8]` argument (AGAST #4837's slot rule).
    "method_arg": ("""\
fn go(d: *Disk) -> i64
    let h = H { n: 0 }
    h.rec((*d).data[1..3])
""", "go(@&d)", 23),
    # No Span expected: a copy, so a write to it leaves the field alone.
    "value_copy": ("""\
fn go(d: *Disk) -> i64
    var c: Vec<u8> = (*d).data[1..3]
    *c.get_ptr(0) = 40
    (c.get(0) as i64) + (c.len() as i64) + ((*d).data.get(1) as i64)
""", "go(@&d)", 49),
    # A method on the field through the deref.
    "method_on_field": ("""\
fn go(d: *Disk) -> i64
    (*d).data.get(2) as i64 + (*d).data.len()
""", "go(@&d)", 6),
}


def _program(name: str) -> str:
    fn, call, _want = FORMS[name]
    return (HEAD + "\n" + fn + "\npub fn main() -> i32\n    var d: Disk = disk()\n"
            + f"    {call} as i32\n")


ROWS = [Row(f"deref_field_slice[{name}]", ALL, Run(_program(name), FORMS[name][2]))
        for name in sorted(FORMS)]


@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(ROWS),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(ROWS)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    table_rows.assert_ritzlib_rows(compiler, table_rows.chunk(ROWS, compiler, chunk), ritz1_bin, tmp_path)
