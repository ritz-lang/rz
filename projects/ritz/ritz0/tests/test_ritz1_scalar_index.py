"""Indexing an integer, float or bool is refused (LANGUAGE_SPEC §7.8, AGAST #3755).

`var n: i64 = 0` then `n[0] = 5` (a STMT_INDEX_ASSIGN) or `let x: i64 = n[0]`
compiled on ritz1 and ritz1_selfhosted, and the binary SIGSEGVd: the emitter
read `n`'s value as an address.  The emitter's own refusal (emitter_types.ritz,
scalar_local_refused) leaves an `i64` / `u64` local alone, since its locals may
carry a pointer as one; Sema binds the declared type, so it can tell.  ritz0
refuses each at the `[`, in index_rules.needs_index's words, and ritz1's Sema
(sema_index_store.ritz, index_scalar_check) now does too.

`s.f[0] = v`, `p.f[0] = v` and `(*p).f[0] = v` on a scalar field, whose target
is a field name, not an Expr, are refused too (AGAST #3799).

`^` marks where the error lands.  A row in RITZ1_ONLY is one ritz0 raises a
traceback on (AGAST #3754) instead of refusing.
"""

import pytest

from index_rules import needs_index
from test_ref_into_value import COMPILERS, _assert_refused

pytestmark = [pytest.mark.integration, pytest.mark.batched]

# One row per path into the check: a name-target store (and its `op=` form),
# a read of a local, param and global, a nested store's inner index, a float
# and a bool base, and an index Sema types through a cast.
ROWS = {
    "store_i64_local": ("i64", "fn f()\n    var n: i64 = 0\n    n^[0] = 5\n"),
    "compound_store": ("i64", "fn f()\n    var n: i64 = 0\n    n^[0] += 5\n"),
    "read_i64_local": ("i64", "fn f() -> i64\n    var n: i64 = 0\n    let x: i64 = n^[0]\n    x\n"),
    "read_u64_param": ("u64", "fn f(n: u64) -> u64\n    n^[1]\n"),
    "global_store": ("i64", "var G: i64 = 0\n\nfn f()\n    G^[0] = 1\n"),
    "global_read": ("i64", "var G: i64 = 0\n\nfn f() -> i64\n    G^[1]\n"),
    "nested_store": ("i64", "fn f()\n    var n: i64 = 0\n    n^[0][1] = 2\n"),
    "store_f64_local": ("f64", "fn f()\n    var n: f64 = 0.0\n    n^[0] = 1.0\n"),
    "read_bool_local": ("bool", "fn f() -> i64\n    var b: bool = true\n    let x: i64 = b^[0] as i64\n    x\n"),
}

S = "struct S\n    f: u32\n\n"

RITZ1_ONLY = {
    "read_cast": ("i64", "fn f(p: *u8) -> i64\n    (p as i64)^[0]\n"),
    "read_field": ("u32", "struct S\n    f: u32\n\nfn f(s: S) -> u32\n    s.f^[1]\n"),
    # AGAST #3799: a field-index store's target is a field name, not an Expr
    # (STMT_LOCAL_FIELD_INDEX_ASSIGN for `s.f[i]` / `p.f[i]`,
    # STMT_MEMBER_INDEX_ASSIGN for `(*p).f[i]`), and each has an `op=` form.
    "local_field_store": ("u32", S + "fn f()\n    var s = S { f: 0 }\n    s.f^[0] = 1\n"),
    "ptr_field_store": ("u32", S + "fn f(p: *S)\n    p.f^[0] = 1\n"),
    "deref_field_store": ("u32", S + "fn f(p: *S)\n    (*p).f^[0] = 1\n"),
    "local_field_compound": ("u32", S + "fn f()\n    var s = S { f: 0 }\n    s.f^[0] += 1\n"),
    "deref_field_compound": ("u32", S + "fn f(p: *S)\n    (*p).f^[0] += 1\n"),
    "spaced_field_store": ("u32", S + "fn f(p: *S)\n    (*p).f ^[0] = 1\n"),
}

MAIN = "\npub fn main() -> i32\n    0\n"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ROWS))
def test_scalar_index_refused(tmp_path, compiler, name):
    ty, body = ROWS[name]
    _assert_refused(compiler, tmp_path, f"scalar_{name}", body + MAIN, needs_index(ty))


@pytest.mark.parametrize("compiler", COMPILERS[1:])
@pytest.mark.parametrize("name", sorted(RITZ1_ONLY))
def test_scalar_index_refused_ritz1(tmp_path, compiler, name):
    ty, body = RITZ1_ONLY[name]
    _assert_refused(compiler, tmp_path, f"scalar_{name}", body + MAIN, needs_index(ty))
