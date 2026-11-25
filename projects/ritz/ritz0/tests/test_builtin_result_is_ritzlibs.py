"""The built-in Result / Option IS ritzlib's (AGAST #4693, LANGUAGE_SPEC §14.1, §10).

The compiler knows `Result<T, E>` and `Option<T>` without an import, and an
arm may name their variants qualified (`Result.Ok(v) =>`, `Option.None =>`)
as well as bare.  ritz0 refused the qualified arm in a file that neither
declares nor imports the enum ("Unknown enum: Result"), and crashed on a
match of a borrowed instance (`o: @Result<i32, E>`: "Match on type ...*
not yet supported"); ritz1 took both, but lowered the borrowed scrutinee to
IR clang refused.  Aaron's decision (2026-11-25): the qualified form names
the built-in, "but it should exact match the one that's imported": one
type, not a twin.  (ritz0 also named the instance it synthesizes
`%"Result$..."` and an imported one `%"enum.<module>.Result$..."`.)

So on all three compilers:

(a) a value built in a file without the import is passed to, returned from
    and matched in a file that imports `ritzlib.result` / `ritzlib.option`,
    and the other way round, with no conversion and no conflict error;
(b) its LLVM type is one definition under one name, with the same body as
    a program that never imports the module;
(c) ritzlib's methods (`is_err`, `unwrap_or`, `is_none`, ...) run on a value
    built where the module wasn't imported.

ritz0's synthesized built-in takes its variants from
name_resolver.BUILTIN_ENUM_VARIANTS, pinned here to ritzlib's declarations,
so the two cannot drift.
"""

import os
import re
import subprocess
from pathlib import Path

import fast_link
import pytest
import ritz_ast as rast
from builtin_types import BUILTIN_TYPES
from name_resolver import BUILTIN_ENUM_VARIANTS
from parser import parse
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# Neither declares nor imports Result / Option; every arm qualified.  (A
# qualified generic enum *value*, `Result.Err(n)`, is refused on every
# compiler, imported or not: §11.3 builds an instance from a bare one.)
NOIMP = """\
pub fn make_err(n: i64) -> Result<i32, i64>
    Err(n)

pub fn make_ok(n: i32) -> Result<i32, i64>
    Ok(n)

pub fn read(r: @Result<i32, i64>) -> i32
    match r
        Result.Ok(v) => v
        Result.Err(e) => e as i32 + 100

pub fn some(n: i32) -> Option<i32>
    Some(n)

pub fn none() -> Option<i32>
    None

pub fn opt(o: Option<i32>) -> i32
    match o
        Option.Some(v) => v
        Option.None => 50
"""

# Imports ritzlib's enums: builds values noimp reads, reads values noimp
# builds, and calls ritzlib's methods on noimp's.
MAIN = """\
import ritzlib.result
import ritzlib.option
import noimp

fn main() -> i32
    let e = make_err(7)
    if !e.is_err()
        return 1
    if e.unwrap_or(9) != 9
        return 2
    let o: Result<i32, i64> = Ok(3)
    if read(@o) != 3
        return 3
    if read(@e) != 107
        return 4
    match make_ok(4)
        Result.Ok(v) =>
            if v != 4
                return 5
        Result.Err(_) => return 6
    if opt(Some(5)) != 5
        return 7
    if opt(None) != 50
        return 8
    if !none().is_none()
        return 9
    if !some(8).is_some()
        return 10
    match some(8)
        Some(v) => v + 3
        None => 11
"""

# The same values, no file importing either module; and with both imported.
ALONE = NOIMP + """
fn main() -> i32
    let e = make_err(7)
    let o: Result<i32, i64> = Ok(3)
    read(@e) + read(@o) + opt(some(1)) + opt(none())
"""
MAIN_IMPORTS = "import ritzlib.result\nimport ritzlib.option\n" + ALONE


def _compile(compiler, work, files):
    """Compile each file to its own `.ll`, as both compilers do (an import's
    fns are only declared); the `.ll` texts, by file."""
    for name, text in files.items():
        (work / name).write_text(text)
    env = dict(os.environ, RITZ_PATH=f"{work}:{RITZ_ROOT}",
               RITZ_CACHE_DIR=str(work / "cas"))
    irs = {}
    for name in files:
        ll = work / name.replace(".ritz", ".ll")
        if compiler == "ritz0":
            proc = run_ritz0([name, "-o", str(ll)], cwd=work, env=env, timeout=300)
        else:
            binary = RITZ1_BUILD / compiler
            # Never skip (#1327): the gate builds both ritz1 binaries first.
            assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
            proc = subprocess.run([str(binary), name, "-o", str(ll)], cwd=work,
                                  env=env, capture_output=True, text=True, timeout=300, check=False)
        assert proc.returncode == 0 and ll.exists(), \
            f"{compiler} refused {name}:\n{(proc.stdout + proc.stderr)[-2000:]}"
        irs[name] = ll.read_text()
    return irs


def _run(compiler, work, irs):
    exe = work / "main"
    lls = [str(work / n.replace(".ritz", ".ll")) for n in irs]
    cmd = ["clang", "-w", *lls, "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], timeout=60, check=False).returncode


# `%Result$i32_i64 = type {...}`, `%"enum.ritz_module_1.Option$i32" = type
# ...`: ritz0 names an enum's type in its module, as it names a declared one.
# Each compiler mangles an instance its own way (`$i32_i64`, `$i32$i64`).
TYPE_DEF = re.compile(r'^%"?((?:enum\.[\w.]+?\.)?(?:Result|Option)[^"\s]*)"? = type (.*)$', re.MULTILINE)
INSTANCES = {"Result<i32, i64>": re.compile(r"(^|\.)Result\$i32[$_]i64$"),
             "Option<i32>": re.compile(r"(^|\.)Option\$i32$")}


def _instances(ir):
    """Each instance's (LLVM name, body).  A module defining a type twice,
    or under a second name (a `Result__<hash>` twin), fails."""
    found = TYPE_DEF.findall(ir)
    names = [n for n, _ in found]
    assert len(names) == len(set(names)), f"a type defined twice: {names}"
    assert not [n for n in names if "__" in n], names
    got = {}
    for ty, pat in INSTANCES.items():
        hits = [(n, body) for n, body in found if pat.search(n)]
        assert len(hits) <= 1, (ty, hits)
        if hits:
            got[ty] = hits[0]
    return got


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_value_built_without_the_import_is_the_imported_type(tmp_path, ritz1_bin, compiler):
    """(a) and (c): across the two files, both ways, ritzlib's methods
    included; (b) each file defines each instance once, under the name and
    with the body the other file gives it."""
    irs = _compile(compiler, tmp_path, {"noimp.ritz": NOIMP, "main.ritz": MAIN})
    noimp, main = _instances(irs["noimp.ritz"]), _instances(irs["main.ritz"])
    assert set(noimp) == set(INSTANCES) and noimp == main, (noimp, main)
    assert _run(compiler, tmp_path, irs) == 11


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_instance_is_laid_out_the_same_with_or_without_the_import(
        tmp_path, ritz1_bin, compiler):
    """(b): a program that never imports ritzlib.result / ritzlib.option
    names and lays out each instance as the same program importing them."""
    imports = tmp_path / "imports"
    imports.mkdir()
    with_import = _instances(_compile(compiler, imports, {"main.ritz": MAIN_IMPORTS})["main.ritz"])
    irs = _compile(compiler, tmp_path, {"main.ritz": ALONE})
    without = _instances(irs["main.ritz"])
    assert set(without) == set(INSTANCES) and without == with_import, (without, with_import)
    assert _run(compiler, tmp_path, irs) == 107 + 3 + 1 + 50


@pytest.mark.parametrize("name", ["Result", "Option"])
def test_ritz0s_builtin_is_ritzlibs_declaration(name):
    """The variants ritz0 synthesizes the built-in from are ritzlib's, in
    order, each payload the same type parameter (the rule #4545 set for
    the built-in views)."""
    path = RITZ_ROOT / (BUILTIN_TYPES[name].replace(".", "/") + ".ritz")
    (enum,) = [i for i in parse(path.read_text()).items
               if isinstance(i, rast.EnumDef) and i.name == name]
    declared = [(v.name, [f.name for f in v.fields]) for v in enum.variants]
    synthesized = [(v, [enum.type_params[p]] if p is not None else [])
                   for v, p in BUILTIN_ENUM_VARIANTS[name]]
    assert declared == synthesized
