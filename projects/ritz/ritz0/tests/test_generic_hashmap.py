#!/usr/bin/env python3
"""A HashMap key type needs ritzlib's `Hash` and `Eq` (AGAST #1858 slice 2,
#4306; LANGUAGE_SPEC §11.5).  One without is refused at the type argument:

    `Nope` doesn't implement `Hash`, which `K` of `HashMap` requires

The map itself (StrView and user-struct keys, growth, collisions and Tombs)
is ritz0/test/test_generic_hashmap.ritz, on the regression matrix.

The row runs on ritz0, ritz1 and ritz1_selfhosted, which must all report the
same `line:col: message`.
"""

import pytest

from test_ref_into_value import COMPILERS, _assert_refused

pytestmark = pytest.mark.integration

NO_HASH = """\
import ritzlib.hash
import ritzlib.hashmap

struct Nope
    k: i64

fn main() -> i32
    var m: HashMap<^Nope, i64> = hashmap_new<Nope, i64>()
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_key_without_hash_refused(compiler, tmp_path):
    _assert_refused(compiler, tmp_path, "no_hash", NO_HASH,
                    "`Nope` doesn't implement `Hash`, which `K` of `HashMap` requires")
