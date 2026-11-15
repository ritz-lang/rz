"""AGAST #3416 (LARB R45a, #3413 step 1): ritz0 warns at each call to a fn
or method declared without `pub` in another file.

Spec §15.1/§15.2: an import brings in only a module's `pub` items, so

    # a.ritz                    # main.ritz
    fn helper() -> i32          import a
        7                       pub fn main() -> i32
                                    helper()        # <- warning here

is a call ritz0 must eventually refuse (#3418). ~650 such sites exist, so
for now it is a located WARNING and nothing else: the build still succeeds,
and the IR is byte-identical to the IR without the check. Its output over
the corpus is the migration list for #3415/#3417.

Covered: free fns, method calls `p.get()`, and the mangled form
`P_get(p)`. Not covered, by the ticket: `extern fn`, monomorph instances,
and calls within one file.
"""

import os
import re
from pathlib import Path

import pytest

import emitter_llvmlite
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent

A_PRIVATE = """\
pub struct P
    v: i32

impl P
    fn get(self: P) -> i32
        self.v

fn helper() -> i32
    7
"""

# Line 5, columns 5 / 18 (the method's name) / 26: helper() + p.get() + P_get(p)
MAIN_CALLS = """\
import a

pub fn main() -> i32
    let p = P { v: 3 }
    helper() + p.get() + P_get(p)
"""


def _compile(tmp_path, a_src, main_src, *extra):
    (tmp_path / "a.ritz").write_text(a_src)
    (tmp_path / "main.ritz").write_text(main_src)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    comp = run_ritz0(["main.ritz", "-o", str(ll), *extra],
                     cwd=tmp_path, env=env, timeout=300)
    assert comp.returncode == 0, comp.stderr
    return comp, ll.read_text()


def _warnings(comp):
    return [l for l in comp.stderr.splitlines() if ": warning: " in l]


def test_cross_file_private_calls_warn_located(tmp_path):
    comp, _ = _compile(tmp_path, A_PRIVATE, MAIN_CALLS)
    assert _warnings(comp) == [
        "main.ritz:5:5: warning: `helper` is private to a.ritz; "
        "mark it `pub` (#3413)",
        "main.ritz:5:18: warning: `P.get` is private to a.ritz; "
        "mark it `pub` (#3413)",
        "main.ritz:5:26: warning: `P_get` is private to a.ritz; "
        "mark it `pub` (#3413)",
    ]


def test_a_deferred_call_emitted_at_each_exit_warns_once(tmp_path):
    a = "fn helper()\n    return\n"
    main = """\
import a

pub fn main() -> i32
    defer helper()
    if 1 == 2
        return 1
    0
"""
    comp, ir = _compile(tmp_path, a, main)
    assert ir.count('call i32 @"helper"') == 2  # once per exit
    assert _warnings(comp) == [
        "main.ritz:4:11: warning: `helper` is private to a.ritz; "
        "mark it `pub` (#3413)"]
    assert len([l for l in comp.stderr.splitlines() if ": note: " in l]) == 1


def test_each_warning_notes_the_declaration(tmp_path):
    """The note names the file to edit: a basename alone is ambiguous across
    packages, and the corpus list (#3415, #3417) is keyed by it."""
    comp, _ = _compile(tmp_path, A_PRIVATE, MAIN_CALLS)
    a = tmp_path / "a.ritz"
    notes = [l for l in comp.stderr.splitlines() if ": note: " in l]
    assert notes == [
        f"{a}:8:1: note: `helper` is declared here",
        f"{a}:5:5: note: `P.get` is declared here",
        f"{a}:5:5: note: `P_get` is declared here",
    ]


def test_warning_leaves_ir_unchanged(tmp_path, monkeypatch, capsys):
    """In-process, so the stub reaches the emitter: the IR with the check
    is byte-identical to the IR with it stubbed out. Fresh sources each
    time, so neither compile is served from the fn cache."""
    import ritz0

    monkeypatch.setenv("RITZ_PATH", f"{tmp_path / 'warned'}:{RITZ_ROOT}")

    def compile_in(sub):
        d = tmp_path / sub
        d.mkdir()
        (d / "a.ritz").write_text(A_PRIVATE)
        (d / "main.ritz").write_text(MAIN_CALLS)
        monkeypatch.setenv("RITZ_PATH", f"{d}:{RITZ_ROOT}")
        assert ritz0.compile_file(str(d / "main.ritz"), str(d / "main.ll"))
        ir = (d / "main.ll").read_text().replace(str(d), "<dir>")
        # The emitter numbers modules per process: a second compile in this
        # one is `ritz_module_2`.
        return re.sub(r"ritz_module_\d+", "ritz_module_N", ir)

    warned = compile_in("warned")
    assert capsys.readouterr().err.count(": warning: ") == 3
    monkeypatch.setattr(emitter_llvmlite.LLVMEmitter,
                        "_check_private_call", lambda *a, **k: None)
    silent = compile_in("silent")
    assert capsys.readouterr().err.count(": warning: ") == 0
    assert warned == silent


A_PUB = A_PRIVATE.replace("    fn get", "    pub fn get").replace(
    "fn helper", "pub fn helper")

SAME_FILE = """\
pub struct Q
    v: i32

impl Q
    fn get(self: Q) -> i32
        self.v

fn own() -> i32
    2

pub fn main() -> i32
    let q = Q { v: 1 }
    own() + q.get() + Q_get(q)
"""

A_EXTERN = """\
extern fn getpid() -> i32
"""

MAIN_EXTERN = """\
import a

pub fn main() -> i32
    getpid()
    0
"""

A_GENERIC = """\
fn ident<T>(x: T) -> T
    x
"""

MAIN_GENERIC = """\
import a

pub fn main() -> i32
    ident<i32>(4)
"""

# a.ritz's pub fn calls a.ritz's own private helper: compiling main (which
# only calls the pub one) and compiling a.ritz itself are both silent.
A_INTERNAL = """\
fn helper() -> i32
    7

pub fn api() -> i32
    helper()
"""

MAIN_API = """\
import a

pub fn main() -> i32
    api()
"""


# a.ritz's generic calls a.ritz's private helper. Its instance is emitted in
# main's unit, but the call is a.ritz's own: the caller's file is the call's.
A_GENERIC_CALLER = """\
fn helper() -> i32
    7

pub fn twice<T>(x: T) -> i32
    helper() + helper()
"""

MAIN_TWICE = """\
import a

pub fn main() -> i32
    twice<i32>(1)
"""


A_DECL = """\
fn getpid() -> i32 = extern
"""

# `E.from` is generated with E's visibility: it has no declaration of its own
# to mark `pub` (marking E is the fix, and E is not a fn).
A_ENUM = """\
import ritzlib.option

enum E: u8
    X = 1
"""

MAIN_ENUM = """\
import ritzlib.option
import a

pub fn main() -> i32
    match E.from(1)
        Some(_) => 0
        None => 1
"""


@pytest.mark.parametrize("a_src,main_src", [
    pytest.param(A_PUB, MAIN_CALLS, id="pub"),
    pytest.param("", SAME_FILE, id="same_file"),
    pytest.param(A_EXTERN, MAIN_EXTERN, id="extern_fn"),
    pytest.param(A_DECL, MAIN_EXTERN, id="decl_only_fn"),
    pytest.param(A_ENUM, MAIN_ENUM, id="generated_from"),
    pytest.param(A_GENERIC, MAIN_GENERIC, id="monomorph"),
    pytest.param(A_INTERNAL, MAIN_API, id="callee_file_own_helper"),
    pytest.param(A_GENERIC_CALLER, MAIN_TWICE, id="instance_calls_own_helper"),
])
def test_no_warning(tmp_path, a_src, main_src):
    comp, _ = _compile(tmp_path, a_src, main_src)
    assert _warnings(comp) == []


def test_module_calling_its_own_private_fn_is_silent(tmp_path):
    """Compiling a.ritz itself: helper is called from its own file."""
    (tmp_path / "a.ritz").write_text(A_INTERNAL)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    comp = run_ritz0(["a.ritz", "-o", str(tmp_path / "a.ll"), "--no-runtime"],
                     cwd=tmp_path, env=env, timeout=300)
    assert comp.returncode == 0, comp.stderr
    assert _warnings(comp) == []


def test_cached_metadata_keeps_visibility(tmp_path):
    """An import served from cached metadata (`_register_items_from_metadata`)
    rebuilds its fns and methods with the visibility they were declared
    with; metadata cached before `is_pub` was recorded reads as `pub`, so it
    never makes a call warn."""
    import json
    import metadata
    from import_resolver import ImportResolver
    from parser import parse

    src = A_PRIVATE + "\npub fn api() -> i32\n    1\n"
    module = parse(src, "a.ritz")
    meta = metadata.metadata_from_json(metadata.metadata_to_json(
        metadata.extract_metadata(module, "a.ritz")))
    resolver = ImportResolver(str(tmp_path), use_cache=False)
    resolver._register_items_from_metadata(meta, "/x/a.ritz")
    assert resolver.functions["helper"][0].is_pub is False
    assert resolver.functions["api"][0].is_pub is True
    (method,) = resolver.impls[0].methods
    assert method.is_pub is False

    old = json.loads(metadata.metadata_to_json(meta))
    for f in old["functions"]:
        del f["is_pub"]
    for m in old["impls"][0]["methods"]:
        del m["is_pub"]
    stale = metadata.metadata_from_json(json.dumps(old))
    resolver = ImportResolver(str(tmp_path), use_cache=False)
    resolver._register_items_from_metadata(stale, "/x/a.ritz")
    assert resolver.functions["helper"][0].is_pub is True
    assert resolver.impls[0].methods[0].is_pub is True


def _build_module():
    import importlib.util
    import sys
    if str(RITZ_ROOT) not in sys.path:
        sys.path.insert(0, str(RITZ_ROOT))
    spec = importlib.util.spec_from_file_location(
        "ritz_build_3416", RITZ_ROOT / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    return build


# A ritz0 that succeeds with a warning: build.py's relay, apart from ritz0.
STUB = """\
#!{python}
import sys
args = sys.argv[1:]
sys.stderr.write("noise that stays quiet\\n")
sys.stderr.write(args[0] + ":1:1: warning: stub (#3416)\\n")
sys.stderr.write(args[0] + ":2:1: note: stub declared here\\n")
with open(args[args.index("-o") + 1], "w") as f:
    f.write("define i32 @main() {{\\n  ret i32 0\\n}}\\n")
"""


@pytest.mark.parametrize("bin_config", [
    pytest.param("", id="hosted"),
    pytest.param('[[bin]]\nname = "kern"\ntarget = "x86_64-unknown-none"\n'
                 'freestanding = true\n', id="freestanding"),
])
def test_build_py_relays_a_successful_compiles_warnings(
        tmp_path, capsys, monkeypatch, bin_config):
    """build.py captures a compile's stderr and shows it only on failure;
    its warning lines are relayed from a successful one, or `./rz build`
    would never show #3416's warning. Only those lines."""
    import stat
    import sys
    import tomllib
    build = _build_module()
    stub = tmp_path / "ritz0_stub.py"
    stub.write_text(STUB.format(python=sys.executable))
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(build, "RITZ0", stub)
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "ritz.toml").write_text(
        f'[package]\nname = "p3416"\nversion = "0.1.0"\n{bin_config}')
    main = pkg / "src" / ("kern.ritz" if bin_config else "main.ritz")
    main.write_text("fn main() -> i32\n    0\n")
    config = tomllib.loads((pkg / "ritz.toml").read_text())
    build.build_package(pkg, config, use_cache=False)  # the link is not the point
    err = capsys.readouterr().err
    assert f"{main}:1:1: warning: stub (#3416)" in err, err
    assert f"{main}:2:1: note: stub declared here" in err, err
    assert "noise that stays quiet" not in err


def test_test_files_relay_their_warnings(tmp_path, capsys, monkeypatch):
    """A test file's compile (`rz test`, `make examples`) is captured too,
    in or out of process; its warnings are relayed like a build's."""
    build = _build_module()
    stderr = "t.ritz:3:5: warning: stub (#3416)\nt.ritz:1:1: note: here\nquiet\n"
    stdout = "  ✓ test_x\n1 passed, 0 failed\n"
    run = lambda *a, **k: build._TestRun(0, stdout, stderr)
    monkeypatch.setattr(build, "_ritz0_test_in_process", run)
    monkeypatch.setattr(build, "_ritz0_test_subprocess", run)
    build.run_test_file(tmp_path / "t.ritz", tmp_path, {}, 60)
    err = capsys.readouterr().err
    assert "t.ritz:3:5: warning: stub (#3416)" in err
    assert "t.ritz:1:1: note: here" in err
    assert "quiet" not in err


@pytest.mark.parametrize("which", ["harness", "dependency"])
def test_test_runner_relays_its_compiles_warnings(tmp_path, capsys, monkeypatch,
                                                  which):
    """test_runner compiles the test file (the harness) and its package's
    modules in subprocesses of its own; their warnings reach the stderr that
    run_test_file relays."""
    import subprocess
    import test_runner
    stderr = "t.ritz:3:5: warning: stub (#3416)\nquiet\n"
    monkeypatch.setattr(test_runner.subprocess, "run", lambda *a, **k:
                        subprocess.CompletedProcess(a, 0, "", stderr))
    if which == "harness":
        err = test_runner._compile_harness("t.ritz", str(tmp_path / "t.ll"),
                                           None, None)
    else:
        err = test_runner._ritz0_compile_dependency(
            Path("ritz0.py"), "t.ritz", str(tmp_path / "t.ll"), None, None)
    assert err is None
    out = capsys.readouterr().err
    assert "t.ritz:3:5: warning: stub (#3416)" in out
    assert "quiet" not in out
