"""ritz1's NFA must refuse to grow past its storage — AGAST #1433 / #1436.

THE DEFECT

The NFA's states and transitions live in caller-owned stack arrays
(ritz1/src/main.ritz: `[4096]NFAState`, `[8192]Transition`). Every
`nfa_add_*` wrote `nfa.states + id` / `nfa.transitions + idx` and bumped the
count with no capacity check, so a grammar one state too large overran
ritz1's stack silently. The only limits written down, `MAX_STATES = 256` and
`MAX_TRANS = 512`, were referenced nowhere and disagreed with the real storage.

WHY IT IS ALSO #1436

Each `nfa_add_*` read its i64 count into an i32 ID (`let id: i32 =
nfa.state_count`). The i64 is there for struct alignment (nfa.ritz's NOTE),
not range, so widening the IDs would buy nothing. The narrowing is lossless
exactly when the count is bounded — which is what this test enforces. With
`nfa_init` taking i32 capacities, count < capacity <= 2^31-1, so the explicit
`as i32` at those sites is lossless by construction rather than by hope.

HOW

A probe gives the NFA N real slots plus one canary slot beyond them, tells
`nfa_init` the capacity is N, and adds items:

    exactly N  -> must succeed (exit 7) — guards an off-by-one in the check
    N + 1      -> must fail loudly (exit 1, message on stderr) and must
                  never reach the canary (exit 3 is the pre-fix behaviour)

One case per `nfa_add_*` function, because each has its own check and fixing
some but not all would otherwise read as "mostly green".

The probe links ritz1's *real* nfa.ritz, compiled by ritz0.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
RITZ1_SRC = RITZ_ROOT / "ritz1" / "src"

CAP = 4

PROBE = """\
import nfa

# {cap} real slots + 1 canary slot beyond them.
fn main() -> i32
    var n: NFA
    var states: [{slots}]NFAState
    var trans: [{slots}]Transition
    var sto: [{slots}]i64
    var stc: [{slots}]i64
    var ti: [{slots}]i64
    states[{cap}].id = 777
    trans[{cap}].kind = 777
    nfa_init(@n, @states[0], @trans[0], @sto[0], @stc[0], @ti[0], {cap}, {cap})
    # Transitions need endpoints; one state is enough for all of them.
    {setup}
    for i in 0..{count}
        {call}
    if states[{cap}].id != 777 or trans[{cap}].kind != 777
        return 3
    return 7
"""

# (per-iteration call, setup line). The state case needs no setup; `0` is a
# no-op statement so the template stays uniform.
ADDERS = [
    pytest.param("nfa_add_state(@n, 0, 0)", "0", id="add_state"),
    pytest.param("nfa_add_char_trans(@n, 0, 0, 97)", "nfa_add_state(@n, 0, 0)", id="add_char_trans"),
    pytest.param("nfa_add_range_trans(@n, 0, 0, 97, 122)", "nfa_add_state(@n, 0, 0)", id="add_range_trans"),
    pytest.param("nfa_add_epsilon_trans(@n, 0, 0)", "nfa_add_state(@n, 0, 0)", id="add_epsilon_trans"),
    pytest.param("nfa_add_any_trans(@n, 0, 0)", "nfa_add_state(@n, 0, 0)", id="add_any_trans"),
]


def _ritz0(src: Path, out: Path, *extra: str) -> None:
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [sys.executable, str(RITZ0), str(src), "-o", str(out), *extra],
        cwd=src.parent, capture_output=True, text=True, env=env, timeout=600,
    )
    assert proc.returncode == 0, (
        f"ritz0 failed on {src.name}:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    )


@pytest.fixture(scope="module")
def nfa_objects(tmp_path_factory) -> tuple[Path, list[Path]]:
    """Compile ritz1's nfa.ritz and its ritzlib deps once."""
    work = tmp_path_factory.mktemp("ritz1_nfa")
    # Symlink rather than copy, so the test can never drift from the source.
    (work / "nfa.ritz").symlink_to(RITZ1_SRC / "nfa.ritz")
    nfa_ll = work / "nfa.ll"
    _ritz0(work / "nfa.ritz", nfa_ll, "--no-runtime")
    sys_ll = work / "lib_sys.ll"
    _ritz0(RITZ_ROOT / "ritzlib" / "sys.ritz", sys_ll, "--no-runtime")
    return work, [nfa_ll, sys_ll]


def _run(nfa_objects, name: str, call: str, setup: str, count: int):
    work, lls = nfa_objects
    case = work / name
    case.mkdir()
    (case / "nfa.ritz").symlink_to(RITZ1_SRC / "nfa.ritz")
    probe = case / "probe.ritz"
    probe.write_text(PROBE.format(cap=CAP, slots=CAP + 1, count=count, call=call, setup=setup))
    probe_ll = case / "probe.ll"
    _ritz0(probe, probe_ll)
    exe = case / "probe"
    link = subprocess.run(
        ["clang", "-O0", "-nostdlib", "-static", "-Wno-override-module",
         str(probe_ll), *map(str, lls), "-o", str(exe)],
        capture_output=True, text=True, timeout=300,
    )
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("call,setup", ADDERS)
def test_filling_to_capacity_succeeds(nfa_objects, call, setup, request):
    # The setup state consumes state capacity, never transition capacity, so
    # every case fills its own table to exactly CAP.
    proc = _run(nfa_objects, f"full_{request.node.callspec.id}", call, setup, CAP)
    assert proc.returncode == 7, (
        f"filling exactly to capacity failed (exit {proc.returncode}) — the "
        f"capacity check is off by one\nstderr: {proc.stderr}"
    )


@pytest.mark.parametrize("call,setup", ADDERS)
def test_one_past_capacity_fails_loudly(nfa_objects, call, setup, request):
    proc = _run(nfa_objects, f"over_{request.node.callspec.id}", call, setup, CAP + 1)
    assert proc.returncode != 3, (
        "wrote past the NFA's storage into the canary slot — nfa_add_* has "
        "no capacity check (#1433)"
    )
    assert proc.returncode == 1, f"expected a loud exit 1, got {proc.returncode}"
    assert "capacity" in proc.stderr, f"no diagnostic on stderr: {proc.stderr!r}"
