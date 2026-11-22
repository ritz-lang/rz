"""AGAST #3606: async's generated `$Future` / `$poll` are compiler internals.

`async fn fetch` becomes a struct `fetch$Future` and a fn `fetch$poll`.  `$`
is not an identifier character (lexer: DOLLAR_OUTSIDE_ASM), so no Ritz
source can spell either: a user's `fn fetch_poll` and `struct fetch_Future`
can sit beside `async fn fetch` without clashing, and writing `fetch_poll(..)`
or `fetch_Future` yourself is an ordinary undefined name.

Before #3606 the generated names were `fetch_Future` / `fetch_poll`, which any
user could spell: a user struct of that name collided with the generated one
(ritz0 crashed defining two `fetch_Future`s), and the resolver and checker
carried #2229's findings recognising the `_Future` suffix.

All three compilers must agree.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ1_SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration


def _compile(compiler: str, tmp_path: Path, src: str, name: str = "t"):
    path = tmp_path / f"{name}.ritz"
    path.write_text(src)
    ll = tmp_path / f"{name}.ll"
    if ll.exists():
        ll.unlink()
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    binary = RITZ1_SELFHOSTED_BIN if compiler == "ritz1_selfhosted" else RITZ1_BIN
    return subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300, check=False)


def _ir(compiler: str, tmp_path: Path, src: str) -> str:
    proc = _compile(compiler, tmp_path, src)
    assert proc.returncode == 0 and (tmp_path / "t.ll").exists(), (
        f"{compiler} failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    return (tmp_path / "t.ll").read_text()


def _run(compiler: str, tmp_path: Path, src: str) -> int:
    _ir(compiler, tmp_path, src)
    exe = tmp_path / f"t_{compiler}"
    cmd = ["clang", "-Wno-override-module", "-O0", str(tmp_path / "t.ll"), "-o", str(exe),
           "-nostdlib", "-no-pie"]
    if compiler in ("ritz1", "ritz1_selfhosted"):
        cmd.insert(1, str(RITZ_START))
    link = fast_link.clang(cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR did not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


# The user's own `fn fetch_poll` and `struct fetch_Future` beside `async fn
# fetch`: 5 (the struct's field) + 6 (the user fn) + 11 (the awaited future).
CLASH = """\
async fn fetch(x: i32) -> i32
    x + 1

struct fetch_Future
    tag: i32

fn fetch_poll(x: i32) -> i32
    x * 2

pub fn main() -> i32
    let a: fetch_Future = fetch_Future { tag: 5 }
    let b: i32 = fetch_poll(3)
    let r: i32 = await fetch(10)
    a.tag + b + r
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_user_name_cannot_clash_with_the_generated_ones(compiler, tmp_path):
    assert _run(compiler, tmp_path, CLASH) == 22


_PLAIN = """\
async fn fetch(x: i32) -> i32
    x + 1

pub fn main() -> i32
    let r: i32 = await fetch(10)
    r
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_generated_names_are_unspellable(compiler, tmp_path):
    ir = _ir(compiler, tmp_path, _PLAIN)
    assert re.search(r"fetch\$Future", ir), (
        "the generated future type should be `fetch$Future`")
    assert re.search(r"fetch\$poll", ir), "the generated poll fn should be `fetch$poll`"
    assert not re.search(r"fetch_Future", ir), "the old, spellable future name survived"
    assert not re.search(r"fetch_poll\b(?!_)", ir), (
        "the old, spellable poll name survived as a generated fn")


# Without a user declaration, the old spellable names name nothing.
_UNDEFINED_POLL = """\
async fn fetch(x: i32) -> i32
    x + 1

pub fn main() -> i32
    fetch_poll(0)
"""

_UNDEFINED_FUTURE = """\
async fn fetch(x: i32) -> i32
    x + 1

pub fn main() -> i32
    var p: fetch_Future = fetch(41)
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_undeclared_poll_is_an_undefined_name(compiler, tmp_path):
    proc = _compile(compiler, tmp_path, _UNDEFINED_POLL)
    assert proc.returncode != 0, f"{compiler} accepted `fetch_poll`: {proc.stderr[-2000:]}"
    out = proc.stdout + proc.stderr
    assert re.search(r"(undefined function|Unknown function): fetch_poll", out), out[-2000:]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_undeclared_future_type_is_an_unknown_name(compiler, tmp_path):
    proc = _compile(compiler, tmp_path, _UNDEFINED_FUTURE)
    assert proc.returncode != 0, f"{compiler} accepted `fetch_Future`: {proc.stderr[-2000:]}"
    out = proc.stdout + proc.stderr
    assert "fetch_Future" in out, out[-2000:]
