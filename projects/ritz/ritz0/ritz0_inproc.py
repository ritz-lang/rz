"""In-process ritz0 for the pytest suite (AGAST #1805).

Why: ~70 `test_*oracle` functions, parametrized over every program they
check, launched ~600 `python3 ritz0.py` processes per session.  Each paid
~0.8 s importing the emitter and llvmlite to compile a program that takes
5-250 ms, only to re-confirm ritz0's answer.

How:

* `run_ritz0(args, cwd=, env=, timeout=)` is a drop-in for
  `subprocess.run(["python3", "ritz0.py", *args], capture_output=True,
  text=True)`.  It forks a child of a multiprocessing *forkserver* that has
  already imported ritz0, and runs ritz0's real `main()` there with `argv`,
  cwd, environment and fds 1/2 set as a subprocess would have them.  CLI
  defaults (ownership checks on, etc.) and `--test` mode are therefore the
  CLI's own, not a re-implementation.

  Each compile is a fresh fork, so the emitter's module-level state cannot
  leak from one compile into the next — that is why this does not simply
  call `ritz0.compile_file` in the pytest process.  Forking from the
  forkserver (a single-threaded process) rather than from pytest also avoids
  fork-with-threads hazards under xdist.

* With `use_cache=True` (off by default: a hit skips ritz0's side effects —
  sig files, incremental "Skipped" — that some tests examine), plain
  compiles (`src -o out.ll [flags]`) are cached for the session by
  sha256 over the flags, RITZ_PATH, and every `.ritz` file in the source's
  directory tree (imports of sibling modules are inputs too).  A hit writes
  the cached `.ll` and replays stdout/stderr with the paths rewritten.

* `ritz0_oracle(src)` is the oracle the `test_ritz1_*` files share:
  compile with ritz0, link `clang -nostdlib`, run, and return
  `Oracle(ir_ok, stdout, rc, diagnostics)`, cached by sha256(src).

Launch accounting: ritz0.py's `main()` appends a line to
$RITZ_TEST_RITZ0_LOG per process; children forked here tag theirs
`inproc `, so the log distinguishes a launched interpreter from a fork.
"""

from __future__ import annotations

import hashlib
import multiprocessing
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
RITZ0_PY = RITZ0_DIR / "ritz0.py"

# Counters for tests and for the session report.
STATS = {"forks": 0, "cache_hits": 0, "oracle_runs": 0, "oracle_hits": 0}

# test_ritz0_inproc.py sets this to make a child sleep, to exercise timeouts.
_CHILD_DELAY_FOR_TESTS = 0.0

_lock = threading.Lock()
_ctx = None
_compile_cache: dict[str, tuple] = {}
_oracle_cache: dict[str, "Oracle"] = {}
_oracle_dir: Path | None = None


def _context():
    global _ctx
    with _lock:
        if _ctx is None:
            if str(RITZ0_DIR) not in sys.path:
                sys.path.insert(0, str(RITZ0_DIR))
            ctx = multiprocessing.get_context("forkserver")
            # The forkserver imports these once; every child inherits them.
            ctx.set_forkserver_preload(["ritz0_inproc", "ritz0"])
            _ctx = ctx
        return _ctx


def _child(argv, cwd, env, out_path, err_path, delay):
    """Body of a forked child: be `python3 ritz0.py *argv`, then _exit."""
    code = 1
    try:
        null = os.open(os.devnull, os.O_RDONLY)
        os.dup2(null, 0)
        out = os.open(out_path, os.O_WRONLY | os.O_TRUNC)
        err = os.open(err_path, os.O_WRONLY | os.O_TRUNC)
        os.dup2(out, 1)
        os.dup2(err, 2)
        if cwd is not None:
            os.chdir(cwd)
        os.environ.clear()
        os.environ.update(env)
        os.environ["RITZ_TEST_RITZ0_INPROC"] = "1"
        if delay:
            time.sleep(delay)
        sys.argv = [str(RITZ0_PY), *argv]
        if str(RITZ0_DIR) not in sys.path:
            sys.path.insert(0, str(RITZ0_DIR))
        import ritz0
        try:
            ritz0.main()
            code = 0
        except SystemExit as e:
            if e.code is None:
                code = 0
            elif isinstance(e.code, int):
                code = e.code
            else:
                print(e.code, file=sys.stderr)
                code = 1
    except BaseException:
        import traceback
        traceback.print_exc()
        code = 1
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            os._exit(code & 0xFF)


def _fork_ritz0(argv, cwd, env, timeout):
    ctx = _context()
    with tempfile.TemporaryDirectory(prefix="ritz0-inproc-") as d:
        out_path = os.path.join(d, "stdout")
        err_path = os.path.join(d, "stderr")
        for p in (out_path, err_path):
            open(p, "w").close()
        proc = ctx.Process(
            target=_child,
            args=(list(argv), cwd, env, out_path, err_path, _CHILD_DELAY_FOR_TESTS),
        )
        with _lock:
            STATS["forks"] += 1
        proc.start()
        proc.join(timeout)
        if proc.is_alive():
            proc.kill()
            proc.join()
            raise subprocess.TimeoutExpired(
                ["ritz0.py", *argv], timeout,
                output=Path(out_path).read_bytes(), stderr=Path(err_path).read_bytes())
        rc = proc.exitcode
        if rc is not None and rc < 0:  # killed by a signal, as subprocess reports
            pass
        return rc, Path(out_path).read_bytes(), Path(err_path).read_bytes()


def _plain_compile(argv):
    """(src, out, flags) if argv is `src -o out [flags without paths]`, else None."""
    args = list(argv)
    if "-o" not in args and "--output" not in args:
        return None
    opt = "-o" if "-o" in args else "--output"
    i = args.index(opt)
    if i + 1 >= len(args):
        return None
    out = args[i + 1]
    rest = args[:i] + args[i + 2:]
    srcs = [a for a in rest if not a.startswith("-")]
    flags = [a for a in rest if a.startswith("-")]
    if len(srcs) != 1 or not srcs[0].endswith(".ritz"):
        return None
    # Flags that take a value would show up as a bare word in `srcs`; we only
    # accept argv whose one bare word is the .ritz source, so none slipped in.
    return srcs[0], out, flags


def _tree_digest(root: Path, h) -> None:
    for p in sorted(root.rglob("*.ritz")):
        h.update(str(p.relative_to(root)).encode() + b"\0")
        h.update(p.read_bytes() + b"\0")


def _compile_key(src: Path, flags, cwd, env) -> str:
    h = hashlib.sha256()
    h.update(repr(sorted(flags)).encode())
    h.update(str(env.get("RITZ_PATH", "")).encode() + b"\0")
    h.update(str(env.get("RITZ_TARGET", "")).encode() + b"\0")
    h.update(src.name.encode() + b"\0")
    _tree_digest(src.parent, h)
    if cwd is not None and Path(cwd).resolve() != src.parent:
        h.update(b"cwd\0" + str(Path(cwd).resolve()).encode())
    return h.hexdigest()


def _note_spawn(what: str) -> None:
    """Tell spawn_guard (if loaded) a ritz0 run happened: it is a compile, so
    the test doing it is `integration` even though no interpreter started."""
    guard = sys.modules.get("spawn_guard")
    if guard is not None:
        guard.note_spawn(what)


def run_ritz0(args, *, cwd=None, env=None, timeout=None, text=True,
              use_cache=False, check=False) -> subprocess.CompletedProcess:
    """Run `ritz0.py *args` without launching an interpreter (see module doc).

    Drop-in for `subprocess.run([python3, ritz0.py, *args], cwd=cwd, env=env,
    timeout=timeout, capture_output=True, text=text)`.
    """
    args = [str(a) for a in args]
    _note_spawn("ritz0 (in-process) " + " ".join(args))
    env = dict(os.environ if env is None else env)
    cwd = str(cwd) if cwd is not None else None
    plain = _plain_compile(args) if use_cache else None
    key = None
    if plain is not None:
        src_s, out_s, flags = plain
        src = Path(cwd or ".", src_s).resolve()
        out = Path(cwd or ".", out_s)
        if src.is_file() and src.parent != RITZ_ROOT and src.parent != RITZ0_DIR:
            key = _compile_key(src, flags, cwd, env)
            with _lock:
                hit = _compile_cache.get(key)
            if hit is not None:
                rc, ll, so, se, old_src, old_out = hit
                if ll is not None:
                    out.write_bytes(ll)
                with _lock:
                    STATS["cache_hits"] += 1
                so = so.replace(old_src.encode(), src_s.encode()).replace(
                    old_out.encode(), out_s.encode())
                se = se.replace(old_src.encode(), src_s.encode()).replace(
                    old_out.encode(), out_s.encode())
                return _completed(args, rc, so, se, text, check)
    rc, so, se = _fork_ritz0(args, cwd, env, timeout)
    if key is not None:
        ll = out.read_bytes() if rc == 0 and out.is_file() else None
        with _lock:
            _compile_cache[key] = (rc, ll, so, se, src_s, out_s)
    return _completed(args, rc, so, se, text, check)


def _completed(args, rc, so, se, text, check):
    if text:
        so = so.decode(errors="replace")
        se = se.decode(errors="replace")
    cp = subprocess.CompletedProcess(["ritz0.py", *args], rc, so, se)
    if check:
        cp.check_returncode()
    return cp


@dataclass(frozen=True)
class Oracle:
    """ritz0's answer for a program: did it compile+link, its stdout and exit code."""
    ir_ok: bool
    stdout: str
    rc: int | None
    diagnostics: str = ""


def _oracle_workdir() -> Path:
    global _oracle_dir
    with _lock:
        if _oracle_dir is None:
            _oracle_dir = Path(tempfile.mkdtemp(prefix="ritz0-oracle-"))
            import atexit
            import shutil
            atexit.register(shutil.rmtree, _oracle_dir, True)
        return _oracle_dir


def ritz0_oracle(src: str, *, stdin: bytes = b"", timeout: int = 60) -> Oracle:
    """Compile `src` with ritz0, link (clang -nostdlib), run; cached by sha256(src).

    `ir_ok` is False when ritz0 rejected the program or its IR did not link;
    then `rc` is None and `diagnostics` holds the compiler/linker output.
    """
    _note_spawn("ritz0_oracle (in-process)")
    digest = hashlib.sha256(src.encode() + b"\0" + stdin).hexdigest()
    with _lock:
        hit = _oracle_cache.get(digest)
        if hit is not None:
            STATS["oracle_hits"] += 1
            return hit
        STATS["oracle_runs"] += 1
    d = _oracle_workdir() / digest[:16]
    d.mkdir(parents=True, exist_ok=True)
    srcf = d / "prog.ritz"
    srcf.write_text(src)
    ll = d / "prog.ll"
    exe = d / "prog"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = run_ritz0([str(srcf), "-o", str(ll)], cwd=d, env=env, timeout=300,
                     use_cache=False)
    if comp.returncode != 0 or not ll.exists():
        res = Oracle(False, "", None, comp.stdout + comp.stderr)
    else:
        link = subprocess.run(["clang", str(ll), "-o", str(exe), "-nostdlib"],
                              cwd=d, capture_output=True, text=True)
        if link.returncode != 0:
            res = Oracle(False, "", None, link.stdout + link.stderr)
        else:
            run = subprocess.run([str(exe)], input=stdin, capture_output=True,
                                 timeout=timeout, cwd=d)
            res = Oracle(True, run.stdout.decode(errors="replace"), run.returncode,
                         run.stderr.decode(errors="replace"))
    with _lock:
        _oracle_cache[digest] = res
    return res
