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

from test_ritz1_builtin_struct_shadow import _run_pkg, ritz1_bin  # noqa: F401

# The exact #1477 shape: struct Ok payload, ctor arms, tail position.
FILE_SIZE_SHAPE = """\
import ritzlib.result

struct St
    dev: i64
    size: i64

fn stat_impl(bad: i64) -> Result<St, i32>
    if bad != 0
        return Err(13)
    return Ok(St { dev: 1, size: 40 })

fn size_of(bad: i64) -> Result<i64, i32>
    var r: Result<St, i32> = stat_impl(bad)
    match r
        Ok(st) => Ok(st.size + 2)
        Err(e) => Err(e)

pub fn main() -> i32
    let a: i64 = match size_of(0)
        Ok(n) => n
        Err(e) => 100 + e as i64
    let b: i64 = match size_of(1)
        Ok(n) => n
        Err(e) => 100 + e as i64
    if a != 42
        return 1
    if b != 113
        return 2
    return 42
"""

# Scalar scrutinee, ctor arms with a non-exhaustive integer match: the
# fallthrough value must be a Result zero, not `add i64 0, 0`.
INT_SCRUT_NON_EXHAUSTIVE = """\
import ritzlib.result

fn classify(x: i64) -> Result<i64, i32>
    match x
        1 => Ok(10)
        2 => Err(20)

pub fn main() -> i32
    let a: i64 = match classify(1)
        Ok(n) => n
        Err(e) => e as i64
    let b: i64 = match classify(2)
        Ok(n) => n
        Err(e) => e as i64
    if a != 10
        return 1
    if b != 20
        return 2
    return 42
"""

# Option<StrView> from ctor arms, exhaustive (`_` arm) and over a
# Result scrutinee.
OPTION_STRVIEW = """\
import ritzlib.option
import ritzlib.result
import ritzlib.strview

fn name_of(x: i64) -> Option<StrView>
    match x
        1 => Some("one")
        2 => Some("three")
        _ => None

fn pick(r: Result<i64, i32>) -> Option<StrView>
    match r
        Ok(n) => Some("ok")
        Err(e) => None

pub fn main() -> i32
    let a: i64 = match name_of(1)
        Some(s) => s.len
        None => 100
    let b: i64 = match name_of(2)
        Some(s) => s.len
        None => 100
    let c: i64 = match name_of(9)
        Some(s) => s.len
        None => 100
    let d: i64 = match pick(Ok(1))
        Some(s) => s.len
        None => 200
    let e: i64 = match pick(Err(1))
        Some(s) => s.len
        None => 200
    if a != 3
        return 1
    if b != 5
        return 2
    if c != 100
        return 3
    if d != 2
        return 4
    if e != 200
        return 5
    return 42
"""

# Mixed arms: a ctor arm and an arm that is a call returning the enum.
MIXED_CALL_ARM = """\
import ritzlib.result

fn fallback(x: i64) -> Result<i64, i32>
    return Err(x as i32)

fn f(x: i64) -> Result<i64, i32>
    match x
        0 => Ok(5)
        _ => fallback(x)

pub fn main() -> i32
    let a: i64 = match f(0)
        Ok(n) => n
        Err(e) => 100 + e as i64
    let b: i64 = match f(7)
        Ok(n) => n
        Err(e) => 100 + e as i64
    if a != 5
        return 1
    if b != 107
        return 2
    return 42
"""

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

PKG_CASES = {
    "file_size_shape": (FILE_SIZE_SHAPE, 42),
    "ritzlib_fs_file_size": (RITZLIB_FS_FILE_SIZE, 42),
    "int_scrut_non_exhaustive": (INT_SCRUT_NON_EXHAUSTIVE, 42),
    "option_strview": (OPTION_STRVIEW, 42),
    "mixed_call_arm": (MIXED_CALL_ARM, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz0_oracle_pkg(tmp_path, name):
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz1_match_ctor_tail_phi(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want
