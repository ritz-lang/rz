"""`clang` for the suite's link steps, without clang's startup (AGAST #2793).

Why: the matrices link one tiny program per case with
`clang [-w] [start.o] main.ll -o main -nostdlib [-no-pie]`.  clang spends
~50 ms of that loading itself (an idle 12-thread host; 150-200 ms under the
gate's load); compiling a 6 KB module is ~2.5 ms of LLVM and linking it ~3 ms
of `ld`.  Thousands of cases paid the startup each.

How: `clang(cmd, **kw)` is a drop-in for `subprocess.run(cmd, **kw)`.

* For the shapes the matrices use — `.ll`/`.o` inputs, `-o`, `-c`, `-w`,
  `-Wno-override-module`, `-nostdlib`, `-no-pie`, `-O0`, and nothing else — each
  `.ll` is compiled to an object by a helper process that has llvmlite
  loaded (LLVM aborts the process on a fatal error, so not in the pytest
  worker), the way clang's cc1 job would: the host triple clang reports
  (clang overrides the module's), its target CPU, PIC, -O0.  The objects
  are then linked by the exact `ld` command clang itself would run, read
  once from `clang -###`.
* Anything else, or any failure on the way — IR that does not parse or
  verify, a helper that died, `ld` refusing — runs the original command
  with `subprocess.run`.  So every refusal a test sees, and its message, is
  real clang's; the fast path only ever stands in for a success.
* `RITZ_TEST_LINK=clang` sends everything to clang.

What it does not cover: llvmlite's LLVM is not clang's (22 vs 21 today).
IR that LLVM 22 accepts and clang 21 rejects would link here.  The gate's
example builds, regression matrix and differential corpus all link with
clang, and every test that asserts a link *fails* calls clang directly.
"""

from __future__ import annotations

import atexit
import json
import os
import select
import shlex
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

STATS = {"fast": 0, "fallback": 0}

# -O0 is clang's default and the level the helper compiles at (AGAST #2808).
_FLAGS = {"-w", "-Wno-override-module", "-nostdlib", "-no-pie", "-c", "-O0"}
# subprocess.run keywords the fast path can honour.
_KWARGS = {"cwd", "capture_output", "text", "check", "timeout"}
# A helper answer slower than this is treated as dead.
_HELPER_TIMEOUT = 120

_lock = threading.Lock()
_helper: subprocess.Popen | None = None
_probe: dict | None = None  # {"triple", "cpu", "ld": {pie: [argv]}}, or {} if unusable

_HELPER_SRC = r"""
import json, sys
import llvmlite.binding as llvm
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()
llvm.initialize_native_asmparser()
triple, cpu = sys.argv[1], sys.argv[2]
tm = llvm.Target.from_triple(triple).create_target_machine(
    cpu=cpu, opt=0, reloc="pic", codemodel="small")
layout = str(tm.target_data)
for line in sys.stdin:
    req = json.loads(line)
    try:
        with open(req["ll"]) as f:
            m = llvm.parse_assembly(f.read())
        m.verify()
        m.triple = triple
        if not m.data_layout:
            m.data_layout = layout
        elif m.data_layout != layout:
            raise ValueError("data layout differs from the target's")
        data = tm.emit_object(m)
        with open(req["obj"], "wb") as f:
            f.write(data)
        resp = {"ok": True}
    except Exception as e:
        resp = {"ok": False, "err": str(e)}
    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()
"""


def _note_spawn(what: str) -> None:
    """A fast link is still a link: tell spawn_guard, as ritz0_inproc does."""
    guard = sys.modules.get("spawn_guard")
    if guard is not None:
        guard.note_spawn(what)


def _parse(cmd) -> dict | None:
    """The plan for `cmd` if the fast path models it, else None."""
    argv = [os.fspath(a) for a in cmd]
    if not argv or Path(argv[0]).name != "clang":
        return None
    out, inputs, flags = None, [], set()
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "-o":
            if i + 1 >= len(argv) or out is not None:
                return None
            out = argv[i + 1]
            i += 2
            continue
        if a in _FLAGS:
            flags.add(a)
        elif not a.startswith("-") and a.endswith((".ll", ".o")):
            inputs.append(a)
        else:
            return None
        i += 1
    if out is None or not inputs:
        return None
    if "-c" in flags:
        if len(inputs) != 1 or not inputs[0].endswith(".ll"):
            return None
    elif "-nostdlib" not in flags:
        return None  # crt files and libc: clang's business
    return {"clang": argv[0], "out": out, "inputs": inputs,
            "compile_only": "-c" in flags, "pie": "-no-pie" not in flags}


def _probe_clang(clang: str) -> dict:
    """Read the triple, CPU and ld command clang would use, from `clang -###`."""
    try:
        with tempfile.TemporaryDirectory(prefix="fast-link-probe-") as d:
            ll = os.path.join(d, "probe.ll")
            obj = os.path.join(d, "__FAST_LINK_IN__.o")
            open(ll, "w").close()
            open(obj, "w").close()
            cc1 = subprocess.run([clang, "-###", "-c", ll, "-o", obj + ".out"],
                                 capture_output=True, text=True, cwd=d)
            job = shlex.split(cc1.stderr.strip().splitlines()[-1])
            triple = job[job.index("-triple") + 1]
            cpu = job[job.index("-target-cpu") + 1]
            ld = {}
            for pie in (True, False):
                cmd = [clang, "-###", "-nostdlib", obj, "-o", "__FAST_LINK_OUT__"]
                if not pie:
                    cmd.insert(2, "-no-pie")
                r = subprocess.run(cmd, capture_output=True, text=True, cwd=d)
                job = shlex.split(r.stderr.strip().splitlines()[-1])
                if job.count(obj) != 1 or job.count("__FAST_LINK_OUT__") != 1:
                    return {}
                ld[pie] = job
            return {"triple": triple, "cpu": cpu, "ld": ld}
    except (OSError, ValueError, IndexError):
        return {}


def _get_probe(clang: str) -> dict:
    global _probe
    if _probe is None:
        _probe = _probe_clang(clang)
    return _probe


def _start_helper(probe: dict) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-I", "-c", _HELPER_SRC, probe["triple"], probe["cpu"]],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, bufsize=1)


def _stop_helper() -> None:
    global _helper
    h, _helper = _helper, None
    if h is not None:
        try:
            h.kill()
            h.wait(timeout=5)
        except Exception:
            pass


atexit.register(_stop_helper)


def _helper_for_tests() -> subprocess.Popen | None:
    return _helper


def _codegen(probe: dict, ll: str, obj: str) -> bool:
    """Compile `ll` to `obj` in the helper. False on any failure."""
    global _helper
    for _ in range(2):  # a helper found dead is restarted once, for the next call
        if _helper is None or _helper.poll() is not None:
            if _helper is not None:
                _stop_helper()
                return False  # died since last time: this call goes to clang
            _helper = _start_helper(probe)
        try:
            _helper.stdin.write(json.dumps({"ll": ll, "obj": obj}) + "\n")
            _helper.stdin.flush()
            ready, _, _ = select.select([_helper.stdout], [], [], _HELPER_TIMEOUT)
            line = _helper.stdout.readline() if ready else ""
        except (OSError, ValueError):
            line = ""
        if not line:
            _stop_helper()
            return False
        return json.loads(line).get("ok") is True
    return False


def _fast(plan: dict, cwd) -> bool:
    """Run `plan` the fast way. True if it produced the output."""
    probe = _get_probe(plan["clang"])
    if not probe:
        return False
    base = Path(cwd) if cwd is not None else Path.cwd()
    out = str(base / plan["out"])
    inputs = [str(base / p) for p in plan["inputs"]]
    if plan["compile_only"]:
        return _codegen(probe, inputs[0], out)
    with tempfile.TemporaryDirectory(prefix="fast-link-") as d:
        objs = []
        for n, p in enumerate(inputs):
            if p.endswith(".o"):
                objs.append(p)
                continue
            obj = os.path.join(d, f"{n}.o")
            if not _codegen(probe, p, obj):
                return False
            objs.append(obj)
        ld = probe["ld"][plan["pie"]]
        argv = []
        for a in ld:
            if a.endswith("__FAST_LINK_IN__.o"):
                argv.extend(objs)
            elif a == "__FAST_LINK_OUT__":
                argv.append(out)
            else:
                argv.append(a)
        r = subprocess.run(argv, capture_output=True, cwd=str(base))
        return r.returncode == 0


def clang(cmd, **kwargs) -> subprocess.CompletedProcess:
    """`subprocess.run(cmd, **kwargs)` for a clang compile/link (module doc)."""
    plan = None
    if os.environ.get("RITZ_TEST_LINK", "") != "clang" and set(kwargs) <= _KWARGS:
        plan = _parse(cmd)
    if plan is not None:
        with _lock:
            ok = _fast(plan, kwargs.get("cwd"))
        if ok:
            with _lock:
                STATS["fast"] += 1
            _note_spawn("fast_link " + " ".join(os.fspath(a) for a in cmd))
            captured = kwargs.get("capture_output", False)
            empty = ("" if kwargs.get("text") else b"") if captured else None
            return subprocess.CompletedProcess(list(cmd), 0, empty, empty)
    with _lock:
        STATS["fallback"] += 1
    return subprocess.run(cmd, **kwargs)
