#!/usr/bin/env python3
"""A generic struct's literal names its type arguments (AGAST #3311).

`Box2 { v: x }` for `struct Box2<X>` names no instance.  ritz0 crashed
(`ValueError: Unknown struct: Box2`, a Python traceback), and ritz1 gave
unrelated errors (`unhandled EXPR_MEMBER`, "`c` is declared `Cell$i32` but its
initialiser is a `Cell`") or, as a call argument, wrote `alloca %Cell`, an
unsized type clang refuses.

Whether a literal may infer its args from its fields, as a generic call does
(LANGUAGE_SPEC section 4.4), is a language question the spec doesn't answer, so
until rz-larb rules on it each compiler refuses the literal where it is
written, saying what to write:

    file:line:col: `Box2` is generic: write its type arguments, `Box2<X> { .. }`

That holds wherever the literal is: a fn, a generic fn's template, an
`impl<T>` method (#3310's args-less spelling; its `Cell<T> { .. }` one is that
ticket's).  A non-generic struct's literal and a spelled-out `Box2<T> { .. }`
still build.

Each row separates a path (docs/TESTING.md, "What a ritz0 pytest case costs").
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import batching
import fast_link
from ritz0_inproc import run_ritz0

pytestmark = [pytest.mark.integration, pytest.mark.batched]

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# Lines 1-7: a plain struct, a one- and a two-parameter generic struct.
HEAD = ("struct T\n    id: i32\n"
        "struct Box2<X>\n    v: X\n"
        "struct Two<A, B>\n    a: A\n    b: B\n")

# name -> (source after HEAD, line:col of the literal, struct, its args)
REFUSED = {
    # The ticket's: an untyped let.
    "untyped_let": ("fn main() -> i32\n    var b = Box2 { v: T { id: 1 } }\n    b.v.id\n",
                    "9:13", "Box2", "X"),
    # A typed let, a fn's tail, a call's argument: each slot names the
    # instance, and still the literal doesn't.  ritz1 wrote `alloca %Box2`
    # for the argument.
    "typed_let": ("fn main() -> i32\n    let b: Box2<i32> = Box2 { v: 3 }\n    b.v\n",
                  "9:24", "Box2", "X"),
    "tail": ("fn mk() -> Box2<i32>\n    Box2 { v: 3 }\nfn main() -> i32\n    mk().v\n",
             "9:5", "Box2", "X"),
    "argument": ("fn f(b: Box2<i32>) -> i32\n    b.v\nfn main() -> i32\n"
                 "    f(Box2 { v: 3 })\n", "11:7", "Box2", "X"),
    # Every parameter is named in the advice.
    "two_parameters": ("fn main() -> i32\n    let t = Two { a: 1, b: 2 }\n    t.a\n",
                       "9:13", "Two", "A, B"),
    # A generic fn's template: refused even with no instance of g.
    "generic_fn": ("fn g<U>(x: U) -> Box2<U>\n    Box2 { v: x }\nfn main() -> i32\n    0\n",
                   "9:5", "Box2", "X"),
    # An `impl<X>` method (#3310's args-less spelling).
    "impl_method": ("impl<X> Box2<X>\n    fn again(self: @Box2<X>) -> Box2<X>\n"
                    "        Box2 { v: self.v }\nfn main() -> i32\n    0\n",
                    "10:9", "Box2", "X"),
}

# name -> (source after HEAD, exit code): the controls.
RUNS = {
    # A plain struct's literal needs no args, beside generic ones.
    "plain_struct": ("fn main() -> i32\n    let t = T { id: 4 }\n    t.id\n", 4),
    # The spelled-out literal, in a fn and in a generic fn's template.
    "spelled_out": ("fn g<U>(x: U) -> Box2<U>\n    Box2<U> { v: x }\nfn main() -> i32\n"
                    "    let b = Box2<T> { v: T { id: 5 } }\n"
                    "    let t = Two<i32, i64> { a: 1, b: 2 }\n"
                    "    b.v.id + g<i32>(t.a).v + t.b as i32\n", 8),
}


def _message(name, args):
    return f"`{name}` is generic: write its type arguments, `{name}<{args}> {{ .. }}`"


def _emit(compiler, path, ll, work):
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{work}")
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=work, env=env,
                          capture_output=True, text=True, timeout=300)


def _link(compiler, ll, work):
    exe = work / "main"
    cmd = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        cmd.insert(2, str(RITZ_START))
    return fast_link.clang(cmd, cwd=work, capture_output=True, text=True), exe


def _batch_compile(compiler, path, work):
    """batching's `compile`: the compile alone, into `work/main.ll` (AGAST #2867)."""
    comp = _emit(compiler, path, work / "main.ll", work)
    return comp.returncode, comp.stdout + comp.stderr


def _batch_build(compiler, path, work):
    """batching.run's `build`: compile and link a batch the way `_run` does a row."""
    ll = work / "main.ll"
    code, output = _batch_compile(compiler, path, work)
    if code != 0 or not ll.exists():
        return False, output, None
    link, exe = _link(compiler, ll, work)
    return link.returncode == 0, link.stderr, exe


def _run(compiler, work, src):
    got = batching.run(compiler, src, _batch_build, compile=_batch_compile)  # #2806, #2867
    if got is not None:
        return got
    batching.per_row()
    path, ll = work / "main.ritz", work / "main.ll"
    path.write_text(src)
    comp = _emit(compiler, path, ll, work)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused:\n{src}\n{out[-2000:]}"
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, f"{compiler}: would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], timeout=60).returncode


@pytest.fixture
def need_ritz1(request):
    def need(compiler):
        if compiler != "ritz0":
            request.getfixturevalue("ritz1_bin")
    return need


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_an_argless_generic_literal_is_refused_at_it(tmp_path, need_ritz1, compiler, name):
    need_ritz1(compiler)
    body, where, struct, args = REFUSED[name]
    src = HEAD + body
    at = tuple(map(int, where.split(":")))
    got = batching.refused(compiler, src, _batch_compile, at=at)
    if got is not None:  # AGAST #2806: this row's diagnostics from its chunk's batch
        out, where = got
    else:
        batching.per_row()
        path, ll = tmp_path / "main.ritz", tmp_path / "main.ll"
        path.write_text(src)
        comp = _emit(compiler, path, ll, tmp_path)
        out = comp.stdout + comp.stderr
        assert comp.returncode != 0, f"{compiler} accepted {name}:\n{src}\n{out}"
    assert "Traceback" not in out, f"{compiler}: {name} crashed:\n{out[-2000:]}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, _message(struct, args)) in found, \
        f"{compiler}: {name}, wanted {where}:\n{src}\n{out[-2000:]}"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_a_literal_that_names_its_struct_builds(tmp_path, need_ritz1, compiler, name):
    need_ritz1(compiler)
    body, code = RUNS[name]
    assert _run(compiler, tmp_path, HEAD + body) == code, f"{compiler}, {name}"
