"""AGAST #1682: a tail `match` whose arms are variant ctors yields the enum.

THE DEFECT

ritzlib/fs.ritz `file_size` (as first written in #1477):

    pub fn file_size(path: StrView) -> Result<i64, i32>
        var r: Result<Stat, i32> = fs_stat_impl(@path, 0)
        match r
            Ok(st) => Ok(st.st_size)
            Err(e) => Err(e)

ritz1 built each arm's `%Result$i64$i32` but joined them with `phi i64`, and
the non-exhaustive fallthrough was `add i64 0, 0`; clang rejected the IR.
#1477 worked around it with a scalar `fs_lstat_size` helper.

THE FIX

Landed with #1667 (variant_ctor_arm_type in ritz1/src/emitter_match.ritz
types the phi with the enum the ctor built, and an aggregate phi takes
`zeroinitializer` on the fallthrough edge). This file pins the #1682 shapes
(struct-payload scrutinee, scalar non-exhaustive scrutinee, Option<StrView>,
a ctor arm mixed with a call arm) and the real ritzlib.fs `file_size`, whose
workaround is reverted here. Mutation-checked: dropping the ctor-arm typing
or emitting the i64 fallthrough turns file_size_shape and
int_scrut_non_exhaustive red with the original clang error.

An inline `return` as an arm body is still a ritz1 parse error: #1689.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

# The real thing: ritzlib.fs `file_size` is the direct tail match again
# (the #1477 `fs_lstat_size` workaround is reverted), and ritz1 must link it.
RITZLIB_FS_FILE_SIZE = """\
import ritzlib.sys
import ritzlib.result
import ritzlib.strview
import ritzlib.fs

pub fn main() -> i32
    var ok: Result<i64, i32> = file_size("/")
    let n: i64 = match ok
        Ok(v) => v
        Err(e) => -1
    if n <= 0
        return 1
    var bad: Result<i64, i32> = file_size("/nonexistent/ritz-1682")
    let e: i64 = match bad
        Ok(v) => -1
        Err(c) => c as i64
    if e != 2
        return 2
    return 42
"""

# The other cases moved to ritz0/test/test_diff_match_ctor_tail_phi.ritz (AGAST #1805), where the
# regression matrix runs them under all three compilers.  This one stays:
# the matrix links ritzlib built by ritz0 into every cell, so its ritz1 cell
# would not be the all-ritz1 build this test checks.
PKG_CASES = {
    "ritzlib_fs_file_size": (RITZLIB_FS_FILE_SIZE, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz0_oracle_pkg(tmp_path, name):
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz1_match_ctor_tail_phi(ritz1_bin, tmp_path, name):
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want
