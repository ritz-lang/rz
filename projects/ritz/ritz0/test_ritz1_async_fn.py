"""AGAST #1456 / #3814: ritz1 lowers `async fn` and `await` as ritz0 does.

#1456 made ritz1 parse `async fn` / `pub async fn` (top level and impl
methods) and `await <expr>`, then refuse each one where written.  #3814 adds
ritz0's lowering (ritz0/async_transform_v2.py, emitter_llvmlite.py
_transform_async_functions / _emit_await) as ritz1/src/async_lower.ritz, an
AST-to-AST pass the driver runs once before any check:

  * `async fn f(p..) -> T` becomes `struct f_Future { __state, p.., the
    locals }`, a constructor `f(p..) -> f_Future` and `f_poll(self:
    *f_Future) -> i32` (-1 is Pending);
  * `async fn main` becomes `__main_future` + `main_poll`, and a sync `main`
    polls it to completion;
  * `await g(..)` outside an async fn drives g's future to completion in place;
  * a bare call to an async fn is refused (LANGUAGE_SPEC §16.2, #1395).

Each run row is compiled, linked and run by ritz0 (the oracle) and by ritz1,
and both must answer the row's exit code.  The rows are ritz0's own async
rows (test_async_call_requires_await.py, test_async_tail_await.py,
test_async_untyped_local.py) and #1456's refusal forms, now run.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
from test_ritz1_builtin_struct_shadow import _run, _run_pkg

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

# The minimal repro from #1456's #1789 survey (65_async_main), verbatim.
REPRO_65 = """\
async fn compute_result(x: i32) -> i32
    x * 7 + 3

async fn main() -> i32
    let result: i32 = await compute_result(5)
    result - 38
"""

_FORTY_TWO = "async fn g() -> i32\n    42\n\n"
_STORE = "fn store(p: *i32, v: i32)\n    *p = v\n\n"
_DBL = "async fn dbl(x: i32) -> i32\n    x * 2\n\n"

# A poll fn that is Pending twice, then Ready(30).
_TICK = """\
var g_n: i32 = 0

fn tick() -> i32
    g_n = g_n + 1
    if g_n < 3
        return 0 - 1
    g_n * 10

async fn waits() -> i32
    let v: i32 = await tick()
    v + 1

"""


def _main(body: str) -> str:
    return f"pub fn main() -> i32\n{body}"


# name -> (program, exit code)
RUNS = {
    "repro_65": (REPRO_65, 0),
    "no_await_body_awaited": (_FORTY_TWO + _main("    let r: i32 = await g()\n    r\n"), 42),
    # A unit async fn's poll is Ready(0); its empty body still runs under await.
    "empty_body_awaited": ("async fn f()\n    pass\n\n" + _main("    await f()\n    3\n"), 3),
    "unit_body_runs": (_STORE + "async fn put(p: *i32)\n    store(p, 7)\n\n"
                       + _main("    var x: i32 = 0\n    await put(@x)\n    x\n"), 7),
    "unit_bare_return": (_STORE + "async fn put(p: *i32, n: i32)\n    if n > 0\n        return\n"
                         "    store(p, 9)\n\n"
                         + _main("    var x: i32 = 1\n    await put(@x, 5)\n    x\n"), 1),
    "unit_with_await": (_STORE + _FORTY_TWO + "async fn put(p: *i32)\n    let v: i32 = await g()\n"
                        "    store(p, v)\n\n"
                        + _main("    var x: i32 = 0\n    await put(@x)\n    x\n"), 42),
    # 55_async_state_machine's chain: each state reads the one before.
    "three_awaits": (_DBL + "async fn chain(x: i32) -> i32\n    let a: i32 = await dbl(x)\n"
                     "    let b: i32 = await dbl(a)\n    let c: i32 = await dbl(b)\n    c / 2\n\n"
                     + _main("    let r: i32 = await chain(10)\n    r\n"), 40),
    # 53_async's test 4: an await nested in the awaited call, as the tail.
    "nested_tail_await": ("fn get_value(x: i32) -> i32\n    x * 10\n\nfn add_one(x: i32) -> i32\n    x + 1\n\n"
                          "async fn e(x: i32) -> i32\n    await add_one(await get_value(x))\n\n"
                          + _main("    let r: i32 = await e(4)\n    r\n"), 41),
    # 55_async_state_machine's test 4: an await in each arm of the tail `if`.
    "conditional_await": (_DBL + "async fn pick(x: i32) -> i32\n    if x > 0\n        await dbl(x)\n"
                          "    else\n        await dbl(0 - x)\n\n"
                          + _main("    let a: i32 = await pick(5)\n    let b: i32 = await pick(0 - 7)\n"
                                  "    a * 10 + b\n"), 114),
    # Pending propagates out of the poll (false); the executor polls again,
    # and reads the value from the future once the poll is true (R78, #3728).
    "pending_polled_by_hand": (_TICK + _main("    var f: waits_Future = waits()\n    var polls: i32 = 1\n"
                                             "    while !waits_poll(@f)\n        polls = polls + 1\n"
                                             "    f.__result + polls * 50\n"), 181),
    # `await` in a sync fn polls until Ready.
    "pending_awaited_in_sync_fn": (_TICK + _main("    let v: i32 = await waits()\n    v + g_n\n"), 34),
    # #3821: the let's value is computed once its await's result is stored.
    "await_inside_let_value": (_DBL + "async fn plus(x: i32) -> i32\n    let v: i32 = (await dbl(x)) + 1\n"
                               "    v * 2\n\n" + _main("    let r: i32 = await plus(5)\n    r\n"), 22),
    # #1318: an untyped await binding takes the awaited fn's result type (R78).  (A non-await `let`
    # ahead of the first await never runs under ritz0's machine, so none here: #3023.)
    "untyped_locals": ("async fn fetch(x: i32) -> i32\n    x\n\n"
                       "async fn go(x: i32) -> i32\n    let v = await fetch(x + 1)\n    v + 1\n\n"
                       + _main("    let r: i32 = await go(4)\n    r\n"), 6),
    # 64_async_io's shape: a struct pointer param handed to a poll fn.
    "struct_ptr_param": ("struct St\n    n: i32\n\nfn st_poll(s: *St) -> i32\n    s.n\n\n"
                         "async fn rd(s: *St) -> i32\n    let r: i32 = await st_poll(s)\n    r + 1\n\n"
                         + _main("    var s: St = St { n: 40 }\n    let r: i32 = await rd(@s)\n    r\n"), 41),
    # blocking_fs's shape: arithmetic on a primitive pointer param, held in the
    # future, strides by its pointee (4 here, not 1).
    "ptr_param_arith": ("fn id(x: i32) -> i32\n    x\n\n"
                        "async fn at(p: *i32, i: i64) -> i32\n    let v: i32 = await id(*(p + i))\n    v\n\n"
                        + _main("    var xs: [3]i32 = [10, 20, 30]\n    let r: i32 = await at(@xs[0], 2)\n    r\n"), 30),
    # `return await` as the last statement is the fn's value.
    "return_await_last": (_DBL + "async fn twice(x: i32) -> i32\n    let a: i32 = await dbl(x)\n"
                          "    return await dbl(a)\n\n"
                          + _main("    let r: i32 = await twice(3)\n    r\n"), 12),
    # `async fn main` awaiting a chain of async fns, an i64 one among them.
    "async_main_chain": ("async fn c(x: i32) -> i64\n    (x * 3) as i64\n\n"
                         "async fn b(x: i32) -> i32\n    let v: i64 = await c(x)\n    (v + 1) as i32\n\n"
                         "async fn main() -> i32\n    let v: i32 = await b(4)\n    v\n", 13),
    "pub_and_attributed": ("pub async fn f() -> i32\n    1\n\n[[inline]]\nasync fn a() -> i32\n    2\n\n"
                           + _main("    let x: i32 = await f()\n    let y: i32 = await a()\n    x + y\n"), 3),
    # The future is a value: an executor keeps it and polls it.
    "future_kept": ("async fn f()\n    pass\n\n" + _main("    var p: f_Future = f()\n    f_poll(@p)\n    5\n"), 5),
    # `await` of a sync fn is its call, in a sync fn, and in a match arm.
    "await_sync_fn": ("fn h() -> i32\n    1\n\nfn k() -> i32\n    let v: i32 = await h()\n    v\n\n"
                      "fn m() -> i32\n    match h()\n        1 => 3\n        _ => await h()\n\n"
                      + _main("    k() * 10 + m()\n"), 13),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RUNS))
def test_async_row_runs_as_ritz0(ritz1_bin, tmp_path, name):
    program, want = RUNS[name]
    assert _run("ritz0", tmp_path, name, program) == want
    assert _run("ritz1", tmp_path, name, program) == want


# name -> (program, (line, col), message); ritz0's words (LANGUAGE_SPEC §16.2).
REFUSALS = {
    "bare_call_statement": (
        "async fn nothing()\n    pass\n\nfn main() -> i32\n    nothing()\n    0\n", (5, 5),
        "calling async fn `nothing` without `await` builds its future and drops it; "
        "its body never runs: write `await nothing(...)`"),
    "bare_call_in_typed_let": (
        "async fn ready() -> i32\n    42\n\nfn main() -> i32\n    let v: i32 = ready()\n    v\n", (5, 5),
        "`v` is declared `i32` but `ready(...)` is an async fn call, which without `await` "
        "is its future `ready_Future`: write `await ready(...)`"),
}


def _compile(compiler: str, tmp_path: Path, text: str):
    src = tmp_path / f"m_{compiler}.ritz"
    src.write_text(text)
    return _compile_file(compiler, tmp_path, src)


def _compile_file(compiler: str, tmp_path: Path, src: Path):
    out = tmp_path / f"{src.stem}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(out)], cwd=tmp_path, env=env, timeout=300)
    return subprocess.run([str(RITZ1_BIN), str(src), "-o", str(out), "-I", str(RITZ_ROOT)],
                          cwd=tmp_path, env=env, capture_output=True, text=True,
                          timeout=300, check=False)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REFUSALS))
def test_bare_async_call_refused_as_ritz0(ritz1_bin, tmp_path, name):
    program, (line, col), message = REFUSALS[name]
    for compiler in ("ritz0", "ritz1"):
        res = _compile(compiler, tmp_path, program)
        assert res.returncode != 0, (compiler, res.stdout, res.stderr)
        assert message in res.stderr, (compiler, res.stderr)
        if compiler == "ritz1":
            errors = [ln for ln in res.stderr.splitlines() if ": error: " in ln]
            assert len(errors) == 1, res.stderr
            assert re.search(rf":{line}:{col}: error: ", errors[0]), res.stderr


# ritz1 doesn't yet start a future with R79's header (`__poll`, `__state`):
# AGAST #4007.
_NO_HEADER = pytest.mark.xfail(strict=True, reason="AGAST #4007: ritz1's futures have no R79 header")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", pytest.param("ritz1", marks=_NO_HEADER)])
def test_imported_async_fn_runs_as_ritz0(ritz1_bin, tmp_path, compiler):
    """#3726: an imported async fn is declared in its importer, defined in its
    file.  The importer allocates its future, so it lays it out from the fn's
    body as the defining file does: `go_Future` holds the header (__poll,
    __state; LARB R79), __result (R78, #3728), x, a and b, and the two
    `fetch_Future`s it awaits (#3727), each the header, __result and x (80
    bytes), which an import stripped to its interface would not know."""
    extra = {"a.ritz": "pub async fn fetch(x: i32) -> i32\n    x + 1\n\n"
                       "pub async fn go(x: i32) -> i32\n    let a: i32 = await fetch(x)\n"
                       "    let b: i32 = await fetch(a)\n    b\n"}
    program = "import a\n\nasync fn main() -> i32\n    let r: i32 = await go(40)\n    r + sizeof(go_Future) as i32\n"
    assert _run_pkg(compiler, tmp_path, "imp_async", program, extra) == 122


def _future_fields(ll: str, name: str) -> list:
    """`name`'s LLVM struct fields, module prefixes dropped: ritz1 names a
    struct `%"struct.ritz_module_1.X"`, ritz0 `%X`."""
    m = re.search(rf'^%"?(?:struct\.\w+\.)?{name}"? = type \{{(.*)\}}$', ll, re.MULTILINE)
    assert m, f"no {name} in the module"
    return [re.sub(r'%"?(?:struct\.\w+\.)?(\w+)"?', r"%\1", f.strip()) for f in m.group(1).split(",")]


@pytest.mark.integration
@_NO_HEADER
def test_if_operand_future_layout_as_ritz0(ritz1_bin, tmp_path):
    """#4190: an awaiting `if` operand's `__if_K` field comes after its
    condition's fields, as the arms' do after it, in both compilers: the
    same `go_Future`, field for field, beside `__for_K` and `__short_K`."""
    program = (_DBL + "async fn go(n: i32) -> i32\n    var s: i32 = 0\n    for i in 0..n\n"
               "        s += 1 + if i > 0 && (await dbl(i)) > 2 then "
               "100 + (if i == 2 then await dbl(5) else await dbl(20)) else 0\n    s\n\n"
               + _main("    await go(4)\n"))
    layouts = []
    for compiler in ("ritz0", "ritz1"):
        res = _compile(compiler, tmp_path, program)
        assert res.returncode == 0, (compiler, res.stdout, res.stderr)
        layouts.append(_future_fields((tmp_path / f"m_{compiler}_{compiler}.ll").read_text(), "go_Future"))
    assert layouts[0] == layouts[1]


PRIVATE_ASYNC_CALLERS = {
    # (main.ritz, line:col of `fetch` at the call)
    "await": ("import a\n\nasync fn main() -> i32\n    let v: i32 = await fetch(41)\n    v\n",
              "4:24"),
    # A bare call is the constructor; ritz0 crashed on its dummy span (#3925).
    "bare": ("import a\n\nfn main() -> i32\n    let f: fetch_Future = fetch(41)\n    0\n",
             "4:27"),
}


@pytest.mark.integration
@pytest.mark.parametrize("caller", sorted(PRIVATE_ASYNC_CALLERS))
def test_private_async_fn_refused_once(ritz1_bin, tmp_path, caller):
    """A private async fn called or awaited from another file is refused
    once, at the call, by its own name (#3413) -- not again for its
    generated poll -- by both compilers, at the same line:col (#3925)."""
    program, at = PRIVATE_ASYNC_CALLERS[caller]
    pkg = tmp_path / "priv"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "a.ritz").write_text("async fn fetch(x: i32) -> i32\n    x + 1\n")
    (pkg / "src" / "main.ritz").write_text(program)
    where = {}
    for compiler in ("ritz0", "ritz1"):
        res = _compile_file(compiler, tmp_path, pkg / "src" / "main.ritz")
        assert res.returncode != 0, (compiler, res.stderr)
        errors = [ln for ln in res.stderr.splitlines() if "private to" in ln]
        assert len(errors) == 1, (compiler, res.stderr)
        m = re.search(r"main\.ritz:(\d+:\d+):( error:)? `fetch` is private to a\.ritz; "
                      r"mark it `pub` \(#3413\)", errors[0])
        assert m, (compiler, res.stderr)
        where[compiler] = m.group(1)
        # The note points at the declaration, which starts at `async`, not
        # at `fn` (#3953: ritz0 said a.ritz:1:7, ritz1 a.ritz:1:1).
        notes = [ln for ln in res.stderr.splitlines() if "is declared here" in ln]
        assert len(notes) == 1, (compiler, res.stderr)
        assert re.search(r"a\.ritz:1:1:( note:)? `fetch` is declared here", notes[0]), \
            (compiler, res.stderr)
    assert where == {"ritz0": at, "ritz1": at}, where


@pytest.mark.integration
def test_private_async_fn_poll_is_exempt(ritz1_bin, tmp_path):
    """The generated `fetch_poll` has no declaration of its own: neither
    compiler refuses a cross-file call to it, and ritz0 no longer crashes
    on its spanless definition (#3925)."""
    pkg = tmp_path / "priv"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "a.ritz").write_text("async fn fetch(x: i32) -> i32\n    x + 1\n")
    (pkg / "src" / "main.ritz").write_text(
        "import a\n\nfn main() -> i32\n    fetch_poll(0 as *fetch_Future) as i32\n")
    for compiler in ("ritz0", "ritz1"):
        res = _compile_file(compiler, tmp_path, pkg / "src" / "main.ritz")
        assert res.returncode == 0, (compiler, res.stderr)


@pytest.mark.integration
def test_blocking_fs_compiles(ritz1_bin, tmp_path):
    """The ticket's module compiles."""
    res = subprocess.run(
        [str(RITZ1_BIN), str(RITZ_ROOT / "ritzlib" / "async" / "blocking_fs.ritz"),
         "-o", str(tmp_path / "out.ll"), "-I", str(RITZ_ROOT)],
        cwd=tmp_path, env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)),
        capture_output=True, text=True, timeout=300, check=False)
    assert res.returncode == 0, res.stderr


@pytest.mark.integration
def test_async_import_path_segment(ritz1_bin, tmp_path):
    """`async` is a keyword, and still a module path segment."""
    res = _compile("ritz1", tmp_path, "import ritzlib.async.tasks\n\nfn main() -> i32\n    0\n")
    assert res.returncode == 0, res.stderr
