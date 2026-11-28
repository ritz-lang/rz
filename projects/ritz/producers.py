"""Which program writes each object a build links (AGAST #4808).

projects/razm/DESIGN.md "Cutover": an unoptimized ELF `.ll` (the small-PIC
and large profiles' modules, both `_start` shims) goes to rllvm, and a
freestanding bin's `.s` goes to razm. Both write relocatable ELF64 that the
same linkers take. A hosted module's `-O2` object stays on clang until rllvm
optimizes (`is_optimized`), and a kernel-model one until its frames fit the
kernel's stacks (`is_kernel`). Routing:

* rllvm exit 0: its object is used.
* rllvm exit 2: the input is outside rllvm's subset (all of ritz0's IR,
  projects/rllvm/tests/corpus/SURVEY.md). clang compiles that file with the
  same flags, after one line naming the file and the construct.
* rllvm exit 1, a signal or a timeout: a build failure, with no fallback
  (AGAST #1731: an object failure is never silent).
* UEFI (a `--target` naming uefi or windows) stays on clang, which writes
  the COFF lld-link takes; so do an optimized (hosted `-O2`) compile and a
  kernel-model (`-mcmodel=kernel`) one.

The back-out switches are RITZ_OBJ_PRODUCER=clang (every `.ll` to clang)
and RITZ_ASM_PRODUCER=as (every `.s` to `as --64`). razm has no per-file
fallback: it assembles every tracked `.s` or the switch is thrown.

Where the programs come from: RITZ_RLLVM / RITZ_RAZM name a prebuilt binary
to use as is. Otherwise each is built on demand from projects/rllvm and
projects/razm, with both switches thrown so a producer is never built by
itself, and copied with its manifest into `TOOLS_DIR`. The compiler is
ritz0, or where ritz0 can't run (the builder image ships no llvmlite) the
ritz1_selfhosted or ritz1 beside it (`tool_compiler`). The copy is current
while every source its manifest lists still has the recorded sha256, under
the same compiler, so an edit to razm, rllvm or a ritzlib module they import
rebuilds them on the next build.

The producer is in every cache key (`obj_identity`, `asm_identity`): an
object or binary built by one producer is never served for another.

Standard library and cache.py only: build_pipeline imports this.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

# Not resolved: the builder image's workspace (projects/builder/entrypoint.sh)
# copies this file in and links the packages, read-only, from the image; a
# resolved ROOT would put TOOLS_DIR in that read-only tree, as build.py's
# resolved symlink once put the runtime objects there (AGAST #4847).
ROOT = Path(os.path.abspath(__file__)).parent   # projects/ritz
PROJECTS = ROOT.parent                          # projects/
BUILD_PY = ROOT / "build.py"

OBJ_PRODUCER_ENV = "RITZ_OBJ_PRODUCER"   # rllvm (the default) | clang
ASM_PRODUCER_ENV = "RITZ_ASM_PRODUCER"   # razm (the default) | as
OBJ_PRODUCERS = ("rllvm", "clang")
ASM_PRODUCERS = ("razm", "as")

# A prebuilt binary, used as is: nothing is built or checked.
TOOL_ENV = {"rllvm": "RITZ_RLLVM", "razm": "RITZ_RAZM"}

# rllvm's exit status for input outside its subset (DESIGN "Routing
# unsupported input"). Anything else non-zero is a failure.
RLLVM_UNSUPPORTED = 2

# `rllvm: FILE:LINE: unsupported: WHAT`, or `rllvm: FILE: unsupported: WHAT`
# when no line applies (a --target triple). As tests/survey.py reads it.
_UNSUPPORTED = re.compile(r"^rllvm: .*?(?::(\d+))?: unsupported: (.*)$")

# How long building one producer may take. A cold ritz0 build of rllvm is
# under a minute; this bounds a wedged one.
TOOL_BUILD_TIMEOUT = 1800

# The copies build_pipeline runs, one directory per tree: a ROOT/build that
# is shared by symlink between trees (get_output_dir, AGAST #3818) must not
# let one tree run the other's tools.
TOOLS_DIR = (ROOT / "build" / "producers"
             / hashlib.sha256(str(ROOT).encode()).hexdigest()[:12])


class ProducerError(Exception):
    """A producer can't be chosen or provided. The build fails with it."""


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def _choice(env: str, allowed: tuple) -> str:
    raw = os.environ.get(env, "").strip()
    if not raw:
        return allowed[0]
    if raw not in allowed:
        raise ProducerError(
            f"{env}={raw!r} is not one of {', '.join(allowed)}")
    return raw


def obj_producer() -> str:
    """`rllvm` or `clang`: RITZ_OBJ_PRODUCER, rllvm when unset."""
    return _choice(OBJ_PRODUCER_ENV, OBJ_PRODUCERS)


def asm_producer() -> str:
    """`razm` or `as`: RITZ_ASM_PRODUCER, razm when unset."""
    return _choice(ASM_PRODUCER_ENV, ASM_PRODUCERS)


def is_coff(flags) -> bool:
    """True for a UEFI object (`--target=x86_64-unknown-windows-gnu`): COFF,
    which only clang writes."""
    for flag in flags:
        if flag.startswith("--target="):
            triple = flag.split("=", 1)[1].lower()
            if "uefi" in triple or "windows" in triple:
                return True
    return False


# The optimization levels clang runs its pass pipeline at. rllvm's v1
# lowering is -O0 whatever level it is given (DESIGN "Optimization bar").
OPTIMIZED = ("-O1", "-O2", "-O3", "-Os", "-Oz")


def is_optimized(flags) -> bool:
    """True for an optimized compile: the hosted `-O2` object
    (OBJ_CLANG_FLAGS). It stays on clang until rllvm optimizes (AGAST #4808,
    rz's call A): at -O0 a hosted suite ran 20x or more slower
    (buddhafinger's test_buffer.ritz: 0.4s on clang -O2's objects, over 10s
    on rllvm's), past its per-test timeout."""
    return any(flag in OPTIMIZED for flag in flags)


def is_kernel(flags) -> bool:
    """True for a kernel-model compile (harland's kernel, -mcmodel=kernel).
    It stays on clang until rllvm's frames shrink (AGAST #4808): v1 gives
    every value its own slot, 10-20x clang -O0's frames (ap_entry 0x2b0
    bytes against 0x20, fmt_i64_into 0x190 against 0x20), and harland's
    4 KiB kernel stacks overflowed, first an AP's boot stack in klog_dec."""
    return "-mcmodel=kernel" in flags


def routes_to_rllvm(flags) -> bool:
    """Whether a `.ll` compiled with `flags` goes to rllvm first: an
    unoptimized, non-kernel ELF compile (the small-PIC and large profiles,
    both shims), when RITZ_OBJ_PRODUCER does not say clang."""
    return (obj_producer() == "rllvm" and not is_coff(flags)
            and not is_optimized(flags) and not is_kernel(flags))


def unsupported_construct(stderr: str) -> str:
    """The construct an exit-2 rllvm named (`type 'metadata'`, line 11), for
    the one-line fallback notice."""
    for text in (stderr or "").splitlines():
        m = _UNSUPPORTED.match(text.strip())
        if m:
            return f"{m.group(2)} (line {m.group(1)})" if m.group(1) else m.group(2)
    lines = (stderr or "").strip().splitlines()
    return lines[0] if lines else "no construct named"


# ---------------------------------------------------------------------------
# Identity: what goes in the cache keys
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()
_MEMO: dict = {}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def clang_version() -> str:
    """The first line of `clang --version` (cas.target_id's probe)."""
    import cas
    return cas.target_id().split("/", 2)[-1]


def obj_identity(flags) -> dict:
    """The producer of a `.ll` compiled with `flags`, for a cache key.

    Routed to rllvm: the sha256 of the rllvm binary, the sha256 of the razm
    sources it was built from, and clang's version line (exit 2 sends a
    file to clang). Otherwise clang's line alone. Raises ProducerError when
    rllvm can't be provided."""
    if not routes_to_rllvm(flags):
        return {"clang": clang_version()}
    rllvm = tool("rllvm")
    return {"rllvm": _binary_sha(rllvm), "razm_lib": _razm_lib_sha(rllvm),
            "clang": clang_version()}


def asm_identity() -> dict:
    """The producer of a `.s`: the razm binary's sha256, or `as`'s version
    line under RITZ_ASM_PRODUCER=as. Raises ProducerError."""
    if asm_producer() == "as":
        return {"as": _as_version()}
    return {"razm": _binary_sha(tool("razm"))}


def stamp_text(identity: dict) -> str:
    """An identity as the one line a `<obj>.producer` stamp holds."""
    return json.dumps(identity, sort_keys=True)


def _binary_sha(path: Path) -> str:
    key = ("sha", str(path), _stat_key(path))
    with _LOCK:
        if key not in _MEMO:
            _MEMO[key] = sha256_file(path)
        return _MEMO[key]


def _stat_key(path: Path):
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_size, st.st_mtime_ns, st.st_ino)


def _razm_lib_sha(rllvm: Path) -> str:
    """sha256 of the razm sources rllvm's manifest lists (rllvm compiles
    razm's library modules into itself). A prebuilt rllvm with no manifest
    has only its own hash, which already covers them."""
    try:
        recorded = json.loads(_manifest(rllvm).read_text())
    except (OSError, ValueError):
        return "unrecorded"
    razm_src = str((PROJECTS / "razm").resolve()) + os.sep
    entries = sorted([os.path.relpath(p, razm_src), h]
                     for p, h in recorded.get("sources", []) if p.startswith(razm_src))
    return hashlib.sha256(json.dumps(entries).encode()).hexdigest()


def _as_version() -> str:
    with _LOCK:
        if "as" not in _MEMO:
            try:
                with subprocess.Popen(["as", "--version"], stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL, text=True) as proc:
                    out, _ = proc.communicate(timeout=30)
                _MEMO["as"] = out.splitlines()[0].strip() if out else "as-unknown"
            except (OSError, subprocess.SubprocessError):
                _MEMO["as"] = "as-missing"
        return _MEMO["as"]


# ---------------------------------------------------------------------------
# The binaries
# ---------------------------------------------------------------------------

def _manifest(binary: Path) -> Path:
    """build_pipeline.binary_manifest_path."""
    return binary.with_name(binary.name + ".manifest.json")


def tool(name: str) -> Path:
    """The rllvm or razm binary to run: $RITZ_RLLVM / $RITZ_RAZM, else
    TOOLS_DIR's copy, built first when it is missing or stale. Raises
    ProducerError when it can't be provided."""
    override = os.environ.get(TOOL_ENV[name], "").strip()
    if override:
        path = Path(override)
        if not (path.is_file() and os.access(path, os.X_OK)):
            raise ProducerError(f"{TOOL_ENV[name]}={override}: not an executable file")
        return path
    with _LOCK:
        memo = ("tool", name)
        if memo in _MEMO:
            return _MEMO[memo]
        dest = TOOLS_DIR / name
        if not is_current(dest):
            _build(name, dest)
        _MEMO[memo] = dest
        return dest


def is_current(binary: Path) -> bool:
    """True only when `binary`'s manifest proves it is what `tool_compiler()`
    would build from today's sources: the binary has the recorded sha256,
    the compiler and its hash are today's, and every recorded source and
    runtime shim still has its recorded sha256. Every doubt is a rebuild."""
    try:
        recorded = json.loads(_manifest(binary).read_text())
        if recorded.get("binary_sha256") != sha256_file(binary):
            return False
        compiler = tool_compiler()
        if recorded.get("compiler") != compiler:
            return False
        if recorded.get("compiler_hash") != _compiler_hash(compiler):
            return False
        for path, digest in [*recorded.get("sources", []), *recorded.get("runtime", [])]:
            if sha256_file(Path(path)) != digest:
                return False
    except (OSError, ValueError, AttributeError, TypeError):
        return False
    return bool(recorded.get("sources"))


def tool_compiler() -> str:
    """The compiler that builds rllvm and razm: ritz0 where its back end
    (llvmlite) imports, else the ritz1-family binary that is built,
    ritz1_selfhosted first. ProducerError when there is none."""
    with _LOCK:
        if "compiler" not in _MEMO:
            import importlib.util
            if importlib.util.find_spec("llvmlite") is not None:
                _MEMO["compiler"] = "ritz0"
            else:
                built = [c for c in ("ritz1_selfhosted", "ritz1")
                         if (ROOT / "ritz1" / "build" / c).is_file()]
                if not built:
                    raise ProducerError(
                        "no compiler to build rllvm and razm with: ritz0 needs "
                        "llvmlite, and no ritz1 is built")
                _MEMO["compiler"] = built[0]
        return _MEMO["compiler"]


def _compiler_hash(compiler: str) -> str:
    with _LOCK:
        key = ("compiler_hash", compiler)
        if key not in _MEMO:
            from cache import compute_compiler_hash
            _MEMO[key] = compute_compiler_hash(ROOT, compiler)
        return _MEMO[key]


def _build(name: str, dest: Path) -> None:
    """Build projects/<name> with `tool_compiler()`, clang and as, and
    publish its binary and manifest at `dest`. One process builds while the
    others wait on the lock, then find the copy current."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest.parent / f"{name}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if is_current(dest):
            return
        compiler = tool_compiler()
        pkg = PROJECTS / name
        print(f"  🔨 building {name} (the {'.ll' if name == 'rllvm' else '.s'} "
              f"producer) from {pkg}", file=sys.stderr)
        env = dict(os.environ)
        # Never built by itself: its own objects come from clang and as.
        env[OBJ_PRODUCER_ENV] = "clang"
        env[ASM_PRODUCER_ENV] = "as"
        env.setdefault("RITZ_PATH", f"{ROOT}{os.pathsep}{PROJECTS}")
        cmd = [sys.executable, str(BUILD_PY), "build", str(pkg), "--compiler", compiler]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env,
                                    cwd=str(pkg), timeout=TOOL_BUILD_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise ProducerError(f"building {name} timed out after {TOOL_BUILD_TIMEOUT}s")
        if result.returncode != 0:
            tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-20:])
            raise ProducerError(f"building {name} failed (exit {result.returncode}):\n{tail}")
        # Where that build linked it: a package reached through a symlink
        # (the builder's workspace) links under ROOT/build/linked/.
        from build_pipeline import get_output_dir
        out = get_output_dir(pkg.resolve(), {"name": "debug"}, invoked_as=pkg)
        _publish(name, out / name, dest)


def _publish(name: str, built: Path, dest: Path) -> None:
    """Copy `built` and its manifest to `dest`, only if the copy is the
    binary the manifest records: another build may have rewritten `built`
    since this one finished (publish_binary's rule, AGAST #1499)."""
    try:
        recorded = json.loads(_manifest(built).read_text())
    except (OSError, ValueError) as e:
        raise ProducerError(f"{name} built without a readable manifest: {e}")
    tmp = dest.with_name(f".{dest.name}.{os.getpid()}.tmp")
    tmp_manifest = _manifest(dest).with_name(f".{_manifest(dest).name}.{os.getpid()}.tmp")
    try:
        shutil.copy2(built, tmp)
        if sha256_file(tmp) != recorded.get("binary_sha256"):
            raise ProducerError(f"{built} changed while {name} was being built: retry")
        tmp_manifest.write_text(json.dumps(recorded, indent=1, sort_keys=True) + "\n")
        os.replace(tmp, dest)
        os.replace(tmp_manifest, _manifest(dest))
    finally:
        tmp.unlink(missing_ok=True)
        tmp_manifest.unlink(missing_ok=True)


def reset_memo() -> None:
    """Forget every memoized tool and hash (tests)."""
    with _LOCK:
        _MEMO.clear()
