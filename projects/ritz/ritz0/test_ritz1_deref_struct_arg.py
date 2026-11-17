"""AGAST #2560: ritz1 passes `*p` (p an `@S` / `@&S` / `*S`) into a
by-value struct param as the struct, not boxed as an i64.

THE DEFECT

    fn go(p: @P) -> i32
        var v: Vec<P> = vec_new<P>()
        v.push(*p)

`v.push(...)` lowers through the UFCS / generic-spec cascade
(emit_ufcs_call, emitter_expr_call.ritz) to `vec_push$P(@&v, item: P)`. Its
scalar->newtype box asks get_expr_type, which reports `*p` as i64, so it
wrote `store i64 %.6, ptr %.7` with `%.6` a `%P`, which clang rejects
(angelo raster/bezier.ritz:122). The instance-method cascade
(emit_expr_method) already skips the box for a `*r` of a struct pointer, so
`h.put(*p)` was fine.

THE MATRIX

pointer form x where p lives x consumer x size, ritz0 as the oracle:

  * pointer form: `@S`, `@&S`, `*S`
  * where: a param of `go`, or a local in `go` holding `@s` / `@&s`
  * consumer: `Vec<S>.push` (UFCS spec) or a user method `h.put(S)`
  * size: 8 bytes (fits an i64), 32 bytes, 280 bytes (byval)

MEASURED ON 5fb6e9bd

  * broken: `Vec<S>.push(*p)` with p an `@S` or `@&S`, param or local, for
    the 8- and 32-byte S.
  * already fine: every `*S` row (get_expr_type types a raw-pointer deref
    as the struct), every user-method row (emit_expr_method's `*r` guard),
    and the 280-byte S (byval; the box skips it).

THE FIX

emit_ufcs_call's box guard skips a `*p` whose pointee is a struct
(deref_pointee_struct_name), as emit_expr_method's already does.

Every program pushes/puts `*p` twice with p.x == 4, then returns the stored
x plus the count, so each exits 6.

Every cell, and the newtype control below, is a row of one table
(test_table_rows.py, AGAST #3889), checked a chunk of rows at a time per
compiler: a chunk is one package build (`pkg_build`).  A row keeps the id its
parametrised test had, less the compiler
(`test_deref_struct_ptr_as_by_value_arg[ritz1-small-ref-param-into-vec_push-was_broken]`
is `deref_struct_ptr_as_by_value_arg[small-ref-param-into-vec_push-was_broken]`
on ritz1), and a failure names each row that failed.
"""

import itertools
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import ritz0_inproc
import test_table_rows as table_rows
from test_table_rows import ALL, Refused, Row, Run

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
_BINS = {
    "ritz1": RITZ_ROOT / "ritz1" / "build" / "ritz1",
    "ritz1_selfhosted": RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted",
}


# ---- a table of packages (AGAST #3889) ---------------------------------------
#
# Every row here imports ritzlib, and each was a build.py package of its own
# (~0.6-1 s a row).  As table rows, a chunk of them is ONE package: its main.ritz
# is the chunk's merged program, and build.py compiles and links it with every
# module the rows import, as it did each row.  test_ritz1_field_recv_push.py,
# test_ritz1_static_method_span_arg.py and test_ritz1_tuple_type.py use these too.

def pkg_compile(compiler, src, work):
    """test_table_rows's `compile`: emit `src`'s module to `work/main.ll` as
    build.py does (no runtime; ritzlib from RITZ_ROOT), and nothing else."""
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = ritz0_inproc.run_ritz0([str(src), "-o", str(ll), "--no-runtime"],
                                      cwd=src.parent, env=env, timeout=300)
    else:
        comp = subprocess.run([str(_BINS[compiler]), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)],
                              cwd=src.parent, env=env, capture_output=True, text=True, timeout=300)
    out = comp.stdout + comp.stderr
    if comp.returncode == 0 and ll.exists():
        unbound = _unbound(ll.read_text())
        if unbound:
            return 1, out + "\nmain.ll names symbols it neither defines nor declares: " + " ".join(unbound)
    return comp.returncode, out


_BOUND = re.compile(r'^(?:define\b[^@\n]*|declare\b[^@\n]*|)@(?:"((?:[^"\\]|\\.)*)"|([-\w.$]+))',
                    re.MULTILINE)

# A symbol, or a string's text (a constant's, inline asm's: no symbol in it).
_TOKEN = re.compile(r'@(?:"((?:[^"\\]|\\.)*)"|([-\w.$]+))|"(?:[^"\\]|\\.)*"')


def _unbound(ll):
    """The `@` symbols `ll` uses but neither defines, declares nor holds as a global.

    batching.leans holds a row's own module to what it declares.  A call ritz1
    emits to a function it never instantiated, undeclared (`call i64
    @Vec$S_push`, AGAST #2562), is invalid IR alone, but in a batch a sibling's
    instance can make the row's code whole; so a row whose own module has one
    is not answered by its batch, and runs alone.
    """
    bound = {q or b for q, b in _BOUND.findall(ll)}
    used = {q or b for q, b in _TOKEN.findall(ll) if q or b}
    return sorted(s for s in used - bound if not s.startswith("llvm.") and not s.isdigit())


def pkg_build(compiler, src, work):
    """test_table_rows's `build`: `src` as the main.ritz of a package build.py
    builds, with the cache (TESTING.md rule 4, `_run_pkg` in
    test_ritz1_builtin_struct_shadow.py).  `work/main.ll` is the module as
    `pkg_compile` emits it, which batching.run_rows holds each row's against."""
    code, out = pkg_compile(compiler, src, work)
    if code != 0:
        return False, out, None
    pkg = work / "pkg"
    (pkg / "src").mkdir(parents=True)
    shutil.copyfile(src, pkg / "src" / "main.ritz")
    (pkg / "ritz.toml").write_text('[package]\nname = "main"\nversion = "0.1.0"\n')
    # TMPDIR: build.py's per-build artifact dir goes under the test's dir, not /tmp.
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT), RITZ_BUILD_CACHE_DIR=str(pkg / ".build-cache"),
               TMPDIR=str(work))
    proc = subprocess.run([sys.executable, str(RITZ_ROOT / "build.py"), "build", str(pkg),
                           "--compiler", compiler],
                          cwd=RITZ_ROOT, env=env, capture_output=True, text=True, timeout=600)
    exe = pkg / "build" / "debug" / "main"
    return proc.returncode == 0 and exe.exists(), proc.stdout + proc.stderr, exe


def assert_table(compiler, rows, work):
    table_rows.assert_rows(compiler, rows, build=pkg_build, compile=pkg_compile, work=work)


SIZES = {
    "small": ("    x: i32\n    y: f32\n", "S { x: 4, y: 1.0 }"),
    "big": (
        "    x: i32\n    b: i64\n    c: i64\n    d: i64\n",
        "S { x: 4, b: 2, c: 3, d: 4 }",
    ),
    "huge": (
        "    x: i32\n" + "".join(f"    p{i}: i64\n" for i in range(34)),
        "S { x: 4, " + ", ".join(f"p{i}: {i}" for i in range(34)) + " }",
    ),
}

# (param/local type, how main/go takes the address)
FORMS = {
    "ref": ("@S", "@s"),
    "mut_ref": ("@&S", "@&s"),
    "raw_ptr": ("*S", "@s"),
}

CONSUMERS = {
    "vec_push": (
        "    var v: Vec<S> = vec_new<S>()\n"
        "    v.push(*p)\n"
        "    v.push(*p)\n"
        "    let q: *S = v.get_ptr(0)\n"
        "    return q.x + v.len() as i32\n"
    ),
    "method": (
        "    var h = H { n: 0, c: 0 }\n"
        "    h.put(*p)\n"
        "    h.put(*p)\n"
        "    return h.n / 2 + h.c\n"
    ),
}


def _program(size: str, form: str, where: str, consumer: str) -> str:
    fields, init = SIZES[size]
    ptype, addr = FORMS[form]
    body = CONSUMERS[consumer]
    if where == "param":
        go = f"fn go(p: {ptype}) -> i32\n" + body
        call = f"    return go({addr})\n"
    else:
        go = f"fn go() -> i32\n    var s = {init}\n    let p: {ptype} = {addr}\n" + body
        call = "    return go()\n"
    return (
        "import ritzlib.gvec\n\n"
        f"struct S\n{fields}\n"
        "struct H\n    n: i32\n    c: i32\n\n"
        "impl H\n"
        "    pub fn put(self:&, p: S)\n"
        "        self.n = self.n + p.x\n"
        "        self.c = self.c + 1\n\n"
        + go
        + "\npub fn main() -> i32\n"
        + f"    var s = {init}\n"
        + call
    )


# The eight rows that produced invalid IR on 5fb6e9bd.
WAS_BROKEN = {
    (size, form, where, "vec_push")
    for size in ("small", "big")
    for form in ("ref", "mut_ref")
    for where in ("param", "local")
}

CELLS = list(itertools.product(SIZES, FORMS, ("param", "local"), CONSUMERS))

ROWS = [
    Row(f"deref_struct_ptr_as_by_value_arg[{size}-{form}-{where}-into-{cons}"
        + ("-was_broken" if (size, form, where, cons) in WAS_BROKEN else "") + "]",
        ("ritz0", "ritz1"), Run(_program(size, form, where, cons), 6))
    for size, form, where, cons in CELLS
]


# Control: `*q` of an `@i64` into a single-field struct (`Vec<M>.push`, M a
# newtype over i64) is an integer, refused since LARB R47 (#3389, #3390): it
# used to take the newtype box.  Only a struct pointee is a struct value, so a
# guard that passed every deref through fails this and not the matrix.
NEWTYPE = """\
import ritzlib.gvec

struct M
    v: i64

fn go(q: @i64) -> i32
    var v: Vec<M> = vec_new<M>()
    v.push(*q)
    v.push(M { v: 5 })
    let r: *M = v.get_ptr(0)
    return r.v as i32 + v.len() as i32

pub fn main() -> i32
    let x: i64 = 4
    return go(@x)
"""

ROWS.append(Row("deref_scalar_ptr_into_newtype_is_refused", ALL,
                Refused(NEWTYPE, "argument 2 of `push` has the wrong type", at=(8, 12))))


@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(ROWS),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(ROWS)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    assert_table(compiler, table_rows.chunk(ROWS, compiler, chunk), tmp_path)
