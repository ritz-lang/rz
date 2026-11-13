"""fast_link.clang: `clang` for the suite's link steps, without clang's startup.

See fast_link.py.  The contract pinned here: the fast path is used for the
plain link shapes the matrices run, produces a binary that behaves as clang's
does, and every failure — bad IR, a helper that died, a linker error, an
argument it does not model — is answered by real clang, so a refusal's exit
code and message are always clang's own.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[1]
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
RITZ1 = RITZ_ROOT / "ritz1" / "build" / "ritz1"

PROGRAM = """\
var G: [4]i64

fn f(n: i64) -> i64
    G[3] = n
    G[3] + 2

pub fn main() -> i32
    f(40) as i32
"""


def _ritz0_ll(tmp_path) -> Path:
    src = tmp_path / "main.ritz"
    src.write_text(PROGRAM)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    assert comp.returncode == 0, comp.stderr
    return ll


def _ritz1_ll(tmp_path, ritz1_bin) -> Path:
    src = tmp_path / "main1.ritz"
    src.write_text(PROGRAM)
    ll = tmp_path / "main1.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = subprocess.run([str(RITZ1), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    assert comp.returncode == 0, comp.stderr
    return ll


def _counts():
    return dict(fast_link.STATS)


def _delta(before):
    return {k: fast_link.STATS[k] - before[k] for k in before}


@pytest.fixture(autouse=True)
def _fast_mode(monkeypatch):
    monkeypatch.delenv("RITZ_TEST_LINK", raising=False)


@pytest.mark.parametrize("pie", [["-no-pie"], []], ids=["no_pie", "pie"])
@pytest.mark.parametrize("warn", [["-w"], ["-Wno-override-module"]], ids=["w", "override"])
def test_ritz0_ir_links_fast_and_runs(tmp_path, pie, warn):
    ll = _ritz0_ll(tmp_path)
    exe = tmp_path / "fast"
    before = _counts()
    link = fast_link.clang(["clang", *warn, str(ll), "-o", str(exe), "-nostdlib", *pie],
                           cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, link.stderr
    assert _delta(before) == {"fast": 1, "fallback": 0}
    assert subprocess.run([str(exe)]).returncode == 42
    # PIE or not, as clang would have made it: ELF e_type ET_DYN (3) / ET_EXEC (2).
    ref = tmp_path / "ref"
    subprocess.run(["clang", *warn, str(ll), "-o", str(ref), "-nostdlib", *pie], check=True)
    assert _elf_type(exe) == _elf_type(ref) == (3 if not pie else 2)


def _elf_type(path) -> int:
    return int.from_bytes(Path(path).read_bytes()[16:18], "little")


def test_ritz1_ir_with_the_start_object(tmp_path, ritz1_bin):
    ll = _ritz1_ll(tmp_path, ritz1_bin)
    exe = tmp_path / "fast1"
    before = _counts()
    link = fast_link.clang(["clang", "-Wno-override-module", str(RITZ_START), str(ll),
                            "-o", str(exe), "-nostdlib", "-no-pie"],
                           cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, link.stderr
    assert _delta(before) == {"fast": 1, "fallback": 0}
    assert subprocess.run([str(exe)]).returncode == 42


def test_the_binary_matches_clangs_behaviour(tmp_path, monkeypatch):
    """Same program, both paths: same exit code, both ELF executables."""
    ll = _ritz0_ll(tmp_path)
    fast_link.clang(["clang", "-w", str(ll), "-o", str(tmp_path / "a"), "-nostdlib"], check=True)
    monkeypatch.setenv("RITZ_TEST_LINK", "clang")
    fast_link.clang(["clang", "-w", str(ll), "-o", str(tmp_path / "b"), "-nostdlib"], check=True)
    for exe in ("a", "b"):
        assert (tmp_path / exe).read_bytes()[:4] == b"\x7fELF"
        assert subprocess.run([str(tmp_path / exe)]).returncode == 42


def test_object_only(tmp_path):
    ll = _ritz0_ll(tmp_path)
    obj = tmp_path / "main.o"
    before = _counts()
    fast_link.clang(["clang", "-w", "-c", str(ll), "-o", str(obj)], check=True)
    assert _delta(before) == {"fast": 1, "fallback": 0}
    exe = tmp_path / "from_obj"
    subprocess.run(["clang", str(obj), "-o", str(exe), "-nostdlib"], check=True)
    assert subprocess.run([str(exe)]).returncode == 42


def test_bad_ir_is_clangs_verdict(tmp_path):
    ll = tmp_path / "bad.ll"
    ll.write_text("define i32 @main() {\n  ret i64 0\n}\n")
    before = _counts()
    link = fast_link.clang(["clang", "-w", str(ll), "-o", str(tmp_path / "bad"), "-nostdlib"],
                           capture_output=True, text=True)
    real = subprocess.run(["clang", "-w", str(ll), "-o", str(tmp_path / "bad2"), "-nostdlib"],
                          capture_output=True, text=True)
    assert _delta(before) == {"fast": 0, "fallback": 1}
    assert link.returncode == real.returncode != 0
    assert link.stderr.replace("bad.ll", "X") == real.stderr.replace("bad.ll", "X")
    assert not (tmp_path / "bad").exists()


def test_bad_ir_to_an_object_is_clangs_verdict(tmp_path):
    ll = tmp_path / "bad.ll"
    ll.write_text("define i32 @f() {\n  ret i64 0\n}\n")
    before = _counts()
    comp = fast_link.clang(["clang", "-w", "-c", str(ll), "-o", str(tmp_path / "bad.o")],
                           capture_output=True, text=True)
    assert _delta(before) == {"fast": 0, "fallback": 1}
    assert comp.returncode != 0 and "error" in comp.stderr
    assert not (tmp_path / "bad.o").exists()


def test_a_link_error_is_clangs_verdict(tmp_path):
    """Valid IR that calls an undefined function: codegen succeeds, ld refuses."""
    ll = tmp_path / "undef.ll"
    ll.write_text("declare i32 @nowhere()\n"
                  "define i32 @_start() {\n  %r = call i32 @nowhere()\n  ret i32 %r\n}\n")
    before = _counts()
    link = fast_link.clang(["clang", "-w", str(ll), "-o", str(tmp_path / "u"), "-nostdlib"],
                           capture_output=True, text=True)
    assert _delta(before) == {"fast": 0, "fallback": 1}
    assert link.returncode != 0
    assert "nowhere" in link.stderr


def test_check_raises_like_subprocess(tmp_path):
    ll = tmp_path / "bad.ll"
    ll.write_text("this is not IR\n")
    with pytest.raises(subprocess.CalledProcessError):
        fast_link.clang(["clang", "-w", str(ll), "-o", str(tmp_path / "x"), "-nostdlib"],
                        check=True, capture_output=True)


def test_explicit_O0_links_fast(tmp_path):
    """-O0 is clang's default and the helper's own level: the same link (#2808)."""
    ll = _ritz0_ll(tmp_path)
    exe = tmp_path / "o0"
    before = _counts()
    fast_link.clang(["clang", "-w", "-O0", str(ll), "-o", str(exe), "-nostdlib"], check=True)
    assert _delta(before) == {"fast": 1, "fallback": 0}
    assert subprocess.run([str(exe)]).returncode == 42


@pytest.mark.parametrize("extra", [["-O2"], ["-O1"], ["-march=native"], ["-lc"], ["-g"], ["x.c"]],
                         ids=["opt", "opt1", "march", "lib", "debug", "c_source"])
def test_anything_else_goes_to_clang(tmp_path, extra):
    ll = _ritz0_ll(tmp_path)
    (tmp_path / "x.c").write_text("int helper(void) { return 0; }\n")
    before = _counts()
    fast_link.clang(["clang", "-w", str(ll), *extra, "-o", str(tmp_path / "e"), "-nostdlib"],
                    cwd=tmp_path, capture_output=True)
    assert _delta(before) == {"fast": 0, "fallback": 1}


def test_env_forces_clang(tmp_path, monkeypatch):
    ll = _ritz0_ll(tmp_path)
    monkeypatch.setenv("RITZ_TEST_LINK", "clang")
    before = _counts()
    fast_link.clang(["clang", "-w", str(ll), "-o", str(tmp_path / "e"), "-nostdlib"], check=True)
    assert _delta(before) == {"fast": 0, "fallback": 1}


def test_a_dead_helper_falls_back_and_restarts(tmp_path):
    ll = _ritz0_ll(tmp_path)
    fast_link.clang(["clang", "-w", str(ll), "-o", str(tmp_path / "a"), "-nostdlib"], check=True)
    fast_link._helper_for_tests().kill()
    before = _counts()
    fast_link.clang(["clang", "-w", str(ll), "-o", str(tmp_path / "b"), "-nostdlib"], check=True)
    assert _delta(before) == {"fast": 0, "fallback": 1}
    assert subprocess.run([str(tmp_path / "b")]).returncode == 42
    before = _counts()
    fast_link.clang(["clang", "-w", str(ll), "-o", str(tmp_path / "c"), "-nostdlib"], check=True)
    assert _delta(before) == {"fast": 1, "fallback": 0}
