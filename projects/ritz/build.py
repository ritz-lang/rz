#!/usr/bin/env python3
"""
🎭 Ritz Build System

A simple build helper that reads ritz.toml configs and compiles examples.

Usage:
    python build.py list              # List all packages
    python build.py build <name>      # Build a specific package
    python build.py build --all       # Build all packages
    python build.py test <name>       # Build and test a package
    python build.py test --all        # Build and test all packages
    python build.py clean             # Remove build artifacts
    python build.py cache-status      # Show cache status
    python build.py cache-clear       # Clear the build cache
"""

import sys
import os
import hashlib
import json
import re
import subprocess
import shutil
import signal
import argparse
import tempfile
import textwrap
import threading
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11

from cache import BuildCache
import cas


ROOT = Path(__file__).parent
RITZ0 = ROOT / "ritz0" / "ritz0.py"
RITZ1_BIN = ROOT / "ritz1" / "build" / "ritz1"   # self-hosted compiler binary
RITZ1_SELFHOSTED_BIN = ROOT / "ritz1" / "build" / "ritz1_selfhosted"  # ritz1 compiled by itself

# Map --compiler values to their ritz1-family binary and the make invocation
# that (re)builds it. Both binaries share the same minimal CLI.
RITZ1_FAMILY_BINS = {
    "ritz1": (RITZ1_BIN, "make -C ritz1 ritz1"),
    "ritz1_selfhosted": (RITZ1_SELFHOSTED_BIN, "make -C ritz1 bootstrap"),
}
RUNTIME_DIR = ROOT / "runtime"

# Architecture-specific runtime files
import platform
ARCH = platform.machine()  # e.g., 'x86_64'
RITZ_START = RUNTIME_DIR / f"ritz_start.{ARCH}.o"           # main(argc, argv)
RITZ_START_NOARGS = RUNTIME_DIR / f"ritz_start_noargs.{ARCH}.o"  # main()
RITZ_START_ENVP = RUNTIME_DIR / f"ritz_start_envp.{ARCH}.o"      # main(argc, argv, envp)


# =============================================================================
# LLVM IR verification (AGAST #1308)
# =============================================================================
#
# Set RITZ_VERIFY_IR=1 to run the LLVM verifier over every module we emit,
# immediately after emission and before clang ever sees it.
#
# The problem this solves: build.py lowers .ll via bare `clang`, so "is this
# IR valid?" was answered by whichever clang happened to be installed. Those
# answers disagreed. On commit eef15af, stage 3 of the regression gate scored
# 42 passed on a clang-21 workstation and 50 passed on the CI runner's older
# clang, and eight examples sat in regression-known-failures-ritz1.txt
# labelled "ritz1 cannot compile this" when the truth was "ritz1 emits IR that
# violates dominance and only the newer verifier objects". For example
# tier2_stdlib_16_tr:
#
#     clang linking failed: invalid LLVM IR input:
#     Instruction does not dominate all uses!
#
# A permissive verifier accepting that does not make the IR valid. It makes a
# real codegen bug invisible until the toolchain moves, whereupon it comes
# back as an unexplained CI break a long way from the commit that caused it.
#
# Pinning clang (see .github/actions/install-toolchain) makes the allowlists
# mean one thing everywhere. This makes them stop depending on the toolchain
# at all: invalid IR fails at the point of emission, naming the function,
# regardless of what clang is on PATH.
#
# Off by default so ordinary `rz build` does not pay for a verifier pass per
# module. CI turns it on for both bootstrap gate steps.
def _ir_verifier_cmd() -> Optional[List[str]]:
    """Return an argv prefix that verifies a .ll file, or None if unavailable.

    Prefers `opt -passes=verify`, which reports every violation with the
    enclosing function named. Falls back to `llvm-as`, whose parser runs the
    same verifier but stops at the first error.

    Ubuntu ships neither under an unsuffixed name outside
    /usr/lib/llvm-N/bin, so an unpinned PATH may legitimately have no
    verifier. That is a reason to warn, not to fail: developers who have not
    opted in should not be blocked, and CI pins the toolchain precisely so
    the tools are present there.
    """
    if shutil.which("opt"):
        return ["opt", "-passes=verify", "-disable-output"]
    if shutil.which("llvm-as"):
        return ["llvm-as", "-o", os.devnull]
    return None


def verify_ir(ll_path: Path, source: Path) -> Optional[str]:
    """Verify freshly emitted IR. Returns an error string, or None if OK.

    No-op unless RITZ_VERIFY_IR is set to a truthy value.
    """
    if os.environ.get("RITZ_VERIFY_IR", "") not in ("1", "true", "yes", "on"):
        return None
    if not ll_path.exists():
        return None

    cmd = _ir_verifier_cmd()
    if cmd is None:
        # Warn once per process; repeating it for all ~100 modules of a
        # bootstrap would bury the build output it is meant to draw attention
        # to.
        global _WARNED_NO_VERIFIER
        if not _WARNED_NO_VERIFIER:
            _WARNED_NO_VERIFIER = True
            print("  ⚠ RITZ_VERIFY_IR set but neither `opt` nor `llvm-as` is on "
                  "PATH; IR not verified. See docs/TOOLCHAIN.md.", file=sys.stderr)
        return None

    result = subprocess.run(cmd + [str(ll_path)], capture_output=True, text=True)
    if result.returncode == 0:
        return None
    return (f"invalid LLVM IR emitted for {source}\n"
            f"    module: {ll_path}\n"
            f"    verifier: {' '.join(cmd)}\n"
            f"{result.stderr.strip()}")


_WARNED_NO_VERIFIER = False

# Ritz links freestanding: no libc, direct syscalls only. A hosted clang does
# not know that. Its loop-idiom recognizer happily rewrites an ordinary byte
# loop into a call to bcmp/memcpy/memset/memmove, so code that never named a
# libc function still ends up referencing one — and the link fails with an
# undefined reference far from the loop that caused it.
#
# This is not hypothetical. Building ritz1 failed with
# `undefined reference to 'bcmp'` from monomorph.ritz, where the only source
# construct was ritzlib's hand-written memcmp comparison loop, inlined and then
# recognized by clang -O2.
#
# Worse, the same pass can rewrite ritzlib's own memcpy loop into a call to
# memcpy, turning the definition into infinite self-recursion.
#
# -ffreestanding tells clang there is no hosted library; -fno-builtin stops it
# assuming the semantics of any libc symbol we do define ourselves. The UEFI
# path already passed -ffreestanding; the Linux path never did.
#
# AGAST #1313 -- IMPORTANT, READ BEFORE TRUSTING THESE FLAGS:
# These flags do NOT prevent the rewrite described above, and never did. They
# are FRONTEND flags, and every site below hands clang an already-emitted .ll
# (`clang -c foo.ll`). The frontend does not run on IR input, so it never
# attaches the `nobuiltin` / "no-builtins" attributes that the IR-level passes
# actually consult. Measured on clang 21.1.8: compiling the same .ll with and
# without these flags produces byte-identical libc references. The bcmp
# incident above was fixed by the flags only because that path still compiled
# from source.
#
# The real fix is that ritz0 and ritz1 now emit "no-builtins" on every
# function definition, so the property travels with the IR and holds no
# matter how clang is invoked. See
# ritz0/emitter_llvmlite.py:_add_alignstack_to_all_functions and
# ritz1/src/emitter.ritz. test_build.py::TestFreestandingIRHasNoLibcCalls
# pins both halves: that the IR stays clean, and that these flags are not the
# mechanism keeping it clean.
#
# They are retained because they are still correct and load-bearing for the
# paths that DO compile C/Ritz source (and for the UEFI target), but do not
# add them somewhere new expecting them to fix a libc-call regression on IR.
FREESTANDING_FLAGS = ["-ffreestanding", "-fno-builtin"]

# AGAST #1731: bounds for the per-source `clang -c -O2 <x>.ll` object compile.
#
# That compile used to run unbounded, and a failure quietly fell back to
# handing the .ll to the link step. Together those hid #1730 for a whole gate:
# under `ulimit -v` clang hit the cap on ritz1's tokens.ll, build.py swallowed
# it and reported success; without the ulimit, every gate hung or OOM'd the
# host (13+ GB clang, WSL down twice).
#
# Now the compile runs under a wall-clock timeout and an RLIMIT_AS cap, and
# any failure (non-zero exit, timeout, cap) fails the build, naming the file,
# the exit status and the stderr tail. There is no fallback. Pathological IR
# is a compiler bug to fix, not something to link around.
#
# Both bounds can be overridden from the environment. Defaults are generous:
# a healthy -O2 compile of the largest ritz1 module takes seconds and well
# under 1 GB.
CLANG_OBJ_TIMEOUT_ENV = "RITZ_CLANG_OBJ_TIMEOUT"   # seconds
CLANG_OBJ_MEM_ENV = "RITZ_CLANG_OBJ_MEM_MB"        # MiB of address space
CLANG_OBJ_TIMEOUT_DEFAULT = 300
CLANG_OBJ_MEM_MB_DEFAULT = 4096
CLANG_OBJ_STDERR_TAIL = 20  # lines of clang stderr shown on failure

# Count of failed object compiles in this process. Every failure fails the
# build, so this exists for tests and post-mortems: it must be zero for any
# build that reported success.
CLANG_OBJ_FAILURES = 0


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        print(f"  ⚠ ignoring {name}={raw!r} (not an integer); using {default}",
              file=sys.stderr)
        return default
    return value if value > 0 else default


def _limit_address_space(limit_bytes: int):
    """Return a preexec_fn that caps the child's address space at `limit_bytes`."""
    def apply() -> None:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
    return apply


# AGAST #1736: a clang crash puts its cause at the top (the backend error,
# then "N. Running pass '...' on function '@f'") and then dozens of stack
# frames, so a bare tail is all frames. These lines are kept from the head.
_CLANG_CRASH_CAUSE = re.compile(
    r"error in backend|LLVM ERROR|^fatal error|Running pass|Program arguments")
CLANG_OBJ_CRASH_HEAD = 8  # most cause lines kept from before the tail


def relay_compiler_warnings(stderr: str) -> None:
    """Show a successful compile's `file:line:col: warning: ...` lines and
    the `note:` lines that go with them.

    The compile's stderr is captured and only shown on failure, so without
    this a warning (AGAST #3416: a call to another file's private fn) would
    never reach a `./rz build`. Only those lines: the rest of a successful
    compile's stderr stays quiet as before. (cas_object, the regression
    matrix's compile, doesn't relay: its programs aren't packages.)"""
    for line in (stderr or "").splitlines():
        if ": warning: " in line or ": note: " in line:
            print(line, file=sys.stderr)


def _stderr_tail(stderr: str, lines: int = CLANG_OBJ_STDERR_TAIL) -> str:
    all_lines = (stderr or "").rstrip().splitlines()
    tail = all_lines[-lines:]
    if not tail:
        return "(no stderr)"
    cause = [ln for ln in all_lines[:-lines] if _CLANG_CRASH_CAUSE.search(ln)]
    if cause:
        return "\n".join(cause[:CLANG_OBJ_CRASH_HEAD] + ["..."] + tail)
    return "\n".join(tail)


# The per-module object compile. Part of every artifact-store key
# (`cas_module_key`), so changing it can never return an object built with the
# old flags.
OBJ_CLANG_FLAGS = ["-c", "-O2", "-fPIC", *FREESTANDING_FLAGS]


def compile_ll_to_obj(ll_path: Path, obj_path: Path, src: Path,
                      flags: Optional[List[str]] = None) -> Optional[str]:
    """Run the bounded `clang <flags>` object compile for one .ll. Return None
    on success.

    `flags` are the target's object flags (`Target.obj_flags`), the hosted
    OBJ_CLANG_FLAGS by default. On failure, increments CLANG_OBJ_FAILURES and
    returns a message naming the file, the exit status (or timeout) and
    clang's stderr tail. The caller must fail the build with it. See the
    AGAST #1731 note above.
    """
    global CLANG_OBJ_FAILURES
    timeout = _env_int(CLANG_OBJ_TIMEOUT_ENV, CLANG_OBJ_TIMEOUT_DEFAULT)
    mem_mb = _env_int(CLANG_OBJ_MEM_ENV, CLANG_OBJ_MEM_MB_DEFAULT)
    if flags is None:
        flags = OBJ_CLANG_FLAGS
    cmd = ["clang", *flags, str(ll_path), "-o", str(obj_path)]

    # Own session, so a timeout kills clang and anything it spawned (cc1 when
    # not integrated), not just the driver.
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True,
        preexec_fn=_limit_address_space(mem_mb * 1024 * 1024),
    )
    try:
        _, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        _, stderr = proc.communicate()
        status = f"timed out after {timeout}s ({CLANG_OBJ_TIMEOUT_ENV})"
    else:
        if proc.returncode == 0:
            return None
        if proc.returncode < 0:
            status = f"killed by signal {-proc.returncode}"
        else:
            status = f"exit status {proc.returncode}"

    CLANG_OBJ_FAILURES += 1
    obj_path.unlink(missing_ok=True)  # never link a partial object
    return (
        f"clang -c failed on {ll_path} (from {src}): {status}\n"
        f"  flags: {' '.join(flags)}\n"
        f"  bounds: timeout {timeout}s, address space {mem_mb} MiB "
        f"({CLANG_OBJ_MEM_ENV})\n"
        f"  stderr tail:\n" + textwrap.indent(_stderr_tail(stderr), "    ")
    )


def report_obj_failures(failures: List[str]) -> None:
    """Report every failed object compile. AGAST #1731: never silent."""
    if not failures:
        return
    n = len(failures)
    print(f"\n  ✗ clang -c failed for {n} IR file{'s' if n != 1 else ''} "
          f"(no fallback; see AGAST #1731):", file=sys.stderr)
    for msg in failures:
        print(f"\n  {msg}", file=sys.stderr)

# Add ritz0 to path for import resolver (must be done before importing)
RITZ0_DIR = ROOT / "ritz0"
if str(RITZ0_DIR) not in sys.path:
    sys.path.insert(0, str(RITZ0_DIR))
import module_interface  # noqa: E402  (ritz0/, G9 interface hashes)

# Global build cache instance. Since AGAST #1808 it only supplies the import
# graph (resolver scans, persisted per worktree) and the compiler fingerprint;
# compiled artifacts live in the shared `cas.ArtifactStore`.
_build_cache: dict[str, BuildCache] = {}

def get_build_cache(compiler: str = "ritz0") -> BuildCache:
    """Get or create the per-compiler build cache.

    The cache stores compiler-emitted IR/bitcode/object files; mixing
    artifacts produced by ritz0 and ritz1 would silently return the wrong
    file on a hit (different IR shape, different ABI assumptions), so each
    compiler gets its own cache directory. See `BuildCache.cache_dir`.
    """
    if compiler not in _build_cache:
        _build_cache[compiler] = BuildCache(project_root=ROOT, compiler=compiler)
    return _build_cache[compiler]


def _verify_ir_enabled() -> bool:
    return os.environ.get("RITZ_VERIFY_IR", "") in ("1", "true", "yes", "on")


def cas_module_key(src: Path, cache: BuildCache, compiler: str,
                   object_flags: Optional[dict] = None) -> Optional[str]:
    """Artifact-store key for one module compiled `--no-runtime` (AGAST #1808).

    Covers the compiler fingerprint, the object flags, RITZ_VERIFY_IR (a hit
    must not skip a verification the caller asked for), the module's source
    and every module in its transitive import closure, resolved by the
    context `cache.set_import_context` was given. None when the closure
    cannot be scanned (a parse error): the caller compiles uncached and the
    compiler reports the real error.

    `object_flags` replaces the hosted object flags for a module built
    another way (compile_freestanding_binary: its target, target_os and
    clang flags), so the two never share an entry.
    """
    flags = {"compiler": compiler, "emit": "no-runtime",
             "obj": OBJ_CLANG_FLAGS if object_flags is None else object_flags,
             "verify_ir": _verify_ir_enabled()}
    # AGAST #1920: every `rz test --all` file unit is its own process and
    # re-keyed the same ritzlib/ritzunit modules (~5 ms each: closure scan,
    # an interface-hash lookup per import, module identities).
    src = Path(src).resolve()
    memo = {"kind": "cas_module_key", "src": str(src), "flags": flags,
            "context": cache._context_key(),
            "compiler_fp": cache._get_current_compiler_hash()}
    hit = closure_memo_get(memo)
    if hit is not None:
        return hit["key"]
    try:
        closure = cache.get_transitive_dependencies(src)
    except Exception:
        return None
    # Persist fresh scans: a fully cached build never writes them otherwise.
    cache._save_imports_db()
    key = _cas_key(src, closure, cache, compiler, flags)
    if key is not None:
        closure_memo_put(memo, {"key": key}, [src, *closure])
    return key


# ---------------------------------------------------------------------------
# Closure memo (AGAST #1920)
# ---------------------------------------------------------------------------
#
# A result computed from a module's import closure (its store key, or the
# closure itself), persisted in the artifact store as
# `objects/<m[:2]>/<m>.keymemo` so a later process skips the resolution.
# `m` digests everything the result depends on except the contents of the
# closure's files (the caller's `material`, plus what this function adds:
# the target, the key schema, the repository root and the parser/resolver
# fingerprint). The entry records the sha256 of every file of the closure
# and is used only while each still has that content. It lives under
# `objects/` so `gc` trims it by least-recent use like any artifact; reading
# it is not counted as a store hit or miss.
#
# Like the import-scan store (cache.IMPORTS_FILE) it trusts that unchanged
# files resolve their imports to the same files: a new file that shadows an
# import elsewhere on the search path is not seen. RITZ_NO_KEY_MEMO=1
# bypasses it.

KEY_MEMO_ENV = "RITZ_NO_KEY_MEMO"
KEY_MEMO_EXT = "keymemo"
KEY_MEMO_SCHEMA = "ritz-keymemo-v1"
_RESOLVER_FP: Optional[str] = None


def _resolver_fingerprint() -> str:
    """What import scanning and resolution (and interface hashes) depend on
    beyond the files themselves: ritz0's parser and resolver, cache.py."""
    global _RESOLVER_FP
    if _RESOLVER_FP is None:
        h = hashlib.sha256(module_interface.parser_fingerprint().encode())
        for f in (RITZ0_DIR / "import_resolver.py", ROOT / "cache.py"):
            h.update(f.name.encode() + b"\0" + f.read_bytes())
        _RESOLVER_FP = h.hexdigest()
    return _RESOLVER_FP


def _closure_memo_id(material: dict) -> Optional[str]:
    if os.environ.get(KEY_MEMO_ENV, "") not in ("", "0"):
        return None
    full = {"schema": KEY_MEMO_SCHEMA, "key_schema": cas.KEY_SCHEMA,
            "target": cas.target_id(), "repo": str(cas.REPO_ROOT),
            "resolver": _resolver_fingerprint(),
            "interfaces": [module_interface.enabled(), module_interface.SCHEMA],
            "material": material}
    blob = json.dumps(full, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def _closure_memo_path(memo_id: str) -> Path:
    return cas.ArtifactStore().path(memo_id, KEY_MEMO_EXT)


def closure_memo_get(material: dict) -> Optional[dict]:
    """The value stored for `material` if every file it was computed from
    still has the content it had, else None."""
    memo_id = _closure_memo_id(material)
    if memo_id is None:
        return None
    path = _closure_memo_path(memo_id)
    try:
        entry = json.loads(path.read_text())
        for f, digest in entry["files"].items():
            if cas.file_sha256(Path(f)) != digest:
                return None
        value = entry["value"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None  # absent, torn, foreign, or a file is gone
    try:
        os.utime(path)  # least-recently-used order for gc
    except OSError:
        pass
    return value


def closure_memo_put(material: dict, value: dict, files) -> None:
    """Record `value` as computed from `material` and the current content of
    `files` (every file of the closure, the root included)."""
    memo_id = _closure_memo_id(material)
    if memo_id is None:
        return
    try:
        entry = {"files": {str(Path(f).resolve()): cas.file_sha256(Path(f)) for f in files},
                 "value": value}
        cas._atomic_write(_closure_memo_path(memo_id),
                          json.dumps(entry, sort_keys=True).encode())
    except OSError:
        pass  # a memo is an optimisation; never fail a build over it


def _cas_key(src: Path, closure, cache: BuildCache, compiler: str,
             flags: dict) -> Optional[str]:
    """cas.module_key for `src` built by `compiler`, its imports digested the
    way that compiler reads them. None if an import does not parse."""
    flags = dict(flags)
    dep_digest = None
    # G9 (AGAST #1810): ritz0 reads its imports' interfaces, not their
    # sources, so its objects depend on interface hashes: a body-only edit
    # to an import keeps every importer's key. G9b (AGAST #1899): ritz1
    # strips each import to the same interface (or less) before anything
    # reads it (main.ritz strip_to_interface), so the same holds for it.
    # RITZ0_NO_INTERFACES is ritz0's switch only; ritz1 always strips.
    if compiler.startswith("ritz1") or (
            compiler == "ritz0" and module_interface.enabled()):
        flags["deps"] = module_interface.SCHEMA
        dep_digest = lambda p: module_interface.interface_hash(str(p))  # noqa: E731
    try:
        return cas.module_key(
            compiler_fp=cache._get_current_compiler_hash(),
            source=Path(src),
            closure=[Path(p) for p in closure],
            flags=flags,
            dep_digest=dep_digest,
        )
    except Exception:
        # An import that does not parse has no interface: compile uncached
        # and let the compiler report the real error.
        return None


def cas_harness_key(src: Path, closure, compiler: str) -> Optional[str]:
    """Artifact-store key of a test file's `--test-table` IR (AGAST #1915).

    `src` is the file the harness compile reads (test_runner's main-stripped
    copy for ritz0, the test file itself for ritz1) and `closure` its
    transitive imports, as test_runner resolved them. Keyed like a module,
    with `emit: test-table` so it never shares an entry with the file's
    `--no-runtime` object. The -O2 object (compile_ll_to_obj) is stored, as
    for every other module (AGAST #1917; it used to be IR linked at -O0, and
    tests that passed only unoptimised hid real bugs). `artifact: o` keeps
    entries from before that change, which hold IR, from being served.
    None when an import does not parse: compile uncached.
    """
    flags = {"compiler": compiler, "emit": "test-table", "artifact": "o"}
    return _cas_key(src, closure, get_build_cache(compiler), compiler, flags)


# BuildCache is not thread-safe; the regression matrix calls in from a pool.
_CAS_CONTEXT_LOCK = threading.Lock()


def cas_closure(src: Path, project_root: Path) -> List[str]:
    """Transitive imports of `src` (itself excluded), resolved in-process the
    way `ritz0 --project-root <project_root>` resolves them. Raises if the
    file (or an import) does not parse. Scans persist in the per-worktree
    import store, so a later process re-parses only changed files."""
    src = Path(src).resolve()
    cache = get_build_cache("ritz0")
    with _CAS_CONTEXT_LOCK:
        cache.set_import_context(project_root=project_root)
        closure = cache.get_transitive_dependencies(src)
        cache._save_imports_db()
    return sorted(p for p in closure if p != str(src))


def cas_object(src: Path, out_obj: Path, *, project_root: Path,
               env: Optional[dict] = None, timeout: int = 120) -> Optional[str]:
    """Write the ritz0 `--no-runtime` object of `src` to `out_obj`, from the
    shared store or by compiling and storing it (AGAST #1894).

    The key and the object pipeline are exactly compile_binary's (ritz0,
    verify_ir, `compile_ll_to_obj`), so an object built here is a hit for
    build.py, test_runner, the regression matrix and ritz1's Makefile alike.
    Returns None on success, else an error naming the file; on failure
    `out_obj` does not exist and nothing is stored.
    """
    src = Path(src).resolve()
    out_obj = Path(out_obj)
    out_obj.parent.mkdir(parents=True, exist_ok=True)
    cache = get_build_cache("ritz0")
    with _CAS_CONTEXT_LOCK:
        cache.set_import_context(project_root=project_root)
        key = cas_module_key(src, cache, "ritz0")
    ll_path = out_obj.with_suffix(".ll")

    def compile_it() -> Optional[str]:
        cmd = [sys.executable, str(RITZ0), str(src), "-o", str(ll_path), "--no-runtime",
               "--project-root", str(project_root)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
        except subprocess.TimeoutExpired:
            return f"{src.name}: ritz0 timed out after {timeout}s"
        if r.returncode != 0:
            out_obj.unlink(missing_ok=True)
            return f"{src.name}: ritz0 failed: {r.stderr[-300:]}"
        error = verify_ir(ll_path, src) or compile_ll_to_obj(ll_path, out_obj, src)
        if error:
            out_obj.unlink(missing_ok=True)
        return error

    if key is None:
        return compile_it()

    def build_fn() -> dict:
        error = compile_it()
        if error:
            raise cas.BuildFailed(error)
        return {"ll": ll_path, "o": out_obj}

    # AGAST #1911: single-flight, so parallel callers missing on one key
    # compile it once between them.
    ident = cas.module_identity(src)
    try:
        # AGAST #2794: fetch, so a hit gc'd before the copy rebuilds.
        cas.ArtifactStore().fetch(
            key, "o", build_fn, out_obj, identity=ident,
            meta={"module": ident, "compiler": "ritz0"})
    except cas.BuildFailed as e:
        return str(e)
    return None


def report_compile_failures(failures: List[Tuple[Path, str]], compiler: str) -> None:
    """Print every source file that failed to compile, not just the first.

    AGAST #1286: the per-file compile loops used to `return None` on the first
    non-zero exit, so a project with N independently-broken files only ever
    showed one of them. Combined with the nondeterministic compile order that
    task also fixed, that meant the *same* tree reported a *different* single
    root cause on every run — three distinct "root causes" were observed for
    `tempest` with zero changes in between.

    Reporting all N is what makes the difference visible: with a stable order
    you get the same first error every time, and with this you get the whole
    list, so nobody has to build N times to discover there were N problems.

    Compile failures are independent — each source is compiled from scratch in
    its own subprocess and does not consume the previous file's artifacts — so
    continuing after one failure yields real diagnostics, not cascade noise.

    Args:
        failures: `(source_path, stderr)` pairs, in compile order.
        compiler: Compiler name, for the message (e.g. `ritz0`, `ritz1`).
    """
    if not failures:
        return

    count = len(failures)
    plural = "file" if count == 1 else "files"
    print(f"\n  ✗ {compiler} failed for {count} source {plural}:", file=sys.stderr)
    for src, stderr in failures:
        detail = (stderr or "").strip() or "(no diagnostic output)"
        # Indent every line so multi-line diagnostics stay visually grouped
        # under the file they belong to.
        indented = "\n".join(f"      {line}" for line in detail.splitlines())
        print(f"\n    {src.name}:\n{indented}", file=sys.stderr)
    print(file=sys.stderr)


def detect_main_signature(source_path: Path) -> int:
    """Detect main function's parameter count from source file.

    Returns:
        0: main() - no arguments
        2: main(argc, argv) - argc and argv
        3: main(argc, argv, envp) - includes envp
    """
    from lexer import Lexer
    from parser import Parser
    import ritz_ast as rast

    try:
        source = source_path.read_text()
        lexer = Lexer(source, str(source_path))
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        module = parser.parse_module()

        for item in module.items:
            if isinstance(item, rast.FnDef) and item.name == 'main':
                return len(item.params)
        return 0  # No main found, assume no args
    except Exception:
        return 0  # On error, default to no args


def get_runtime_object(num_params: int) -> Path:
    """Get the appropriate runtime object file for main's signature."""
    if num_params >= 3:
        return RITZ_START_ENVP
    elif num_params >= 2:
        return RITZ_START
    else:
        return RITZ_START_NOARGS


def ensure_runtime_object(obj_path: Path) -> bool:
    """Build a runtime `_start` object from its tracked `.ll` if needed.

    The runtime objects under `runtime/` are *derived* artifacts: the `.ll`
    sources are tracked in git, the `.o` files are gitignored. Previously
    nothing built them — `runtime/Makefile` existed but no build path ever
    invoked it, so both `build.py` and `ritz1/Makefile` simply asserted the
    `.o` was already on disk and told the user to "run make in runtime/".

    That made a fresh clone unbuildable: every package with
    `link_runtime` failed, and CI (which always starts from a clean
    checkout) could never link a hosted binary. It only appeared to work
    locally because stale `.o` files lingered in developers' trees — which
    is worse than failing, because an edit to a `.ll` shim would silently
    link against a months-old object.

    A derived artifact must be a dependency, not a documented manual step.
    Compile on demand, keyed on mtime so repeat builds stay free.

    Returns True if `obj_path` exists (or was just built) and is current.
    """
    ll_path = obj_path.with_suffix(".ll")
    if not ll_path.exists():
        print(f"  ✗ Runtime source not found: {ll_path}", file=sys.stderr)
        return False

    # Up to date? Nothing to do.
    if obj_path.exists() and obj_path.stat().st_mtime >= ll_path.stat().st_mtime:
        return True

    # Build into a private temp file and rename it into place (AGAST #2792).
    # The object is at a fixed path shared by every concurrent build (xdist
    # workers, parallel rooms' tools): written in place, a second process
    # sees an existing, newer-than-.ll, half-written object and links it.
    # rename() is atomic on one filesystem, hence the same directory.
    obj_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = obj_path.with_name(f".{obj_path.name}.{os.getpid()}.tmp")
    try:
        result = subprocess.run(
            ["clang", "-c", "-o", str(tmp_path), str(ll_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  ✗ Failed to build runtime object {obj_path.name}:\n"
                  f"{result.stderr}", file=sys.stderr)
            return False
        os.replace(tmp_path, obj_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return True


# =============================================================================
# RFC #109 Phase 1: Entry Point Resolution, Source Discovery, Build Profiles
# =============================================================================

def resolve_entry_point(entry: str, pkg_dir: Path, sources: list[str]) -> tuple[Path, str] | None:
    """Resolve entry = "module::function" to (file_path, function_name).

    Per RFC #109 §2.4:
    - Parse entry = "path.to.module::function"
    - Convert module path to file: path/to/module.ritz
    - Search in sources directories
    - Return (file_path, function_name) or None if not found

    Examples:
        main::main          → src/main.ritz, fn main()
        http.server::run    → src/http/server.ritz, fn run()
        tools.cli::main     → src/tools/cli.ritz, fn main()
    """
    if "::" not in entry:
        return None

    module_path, fn_name = entry.rsplit("::", 1)

    # Convert module path (dots) to file path (slashes)
    # main → main.ritz
    # http.server → http/server.ritz
    file_rel_path = module_path.replace(".", "/") + ".ritz"

    # Search in each source directory
    for src_spec in sources:
        # Handle exclusion patterns (skip them for search)
        if src_spec.startswith("!"):
            continue

        # Normalize source spec to directory
        src_dir = pkg_dir / src_spec.split("*")[0].rstrip("/")
        if not src_dir.is_dir():
            continue

        candidate = src_dir / file_rel_path
        if candidate.exists():
            return (candidate, fn_name)

    return None


def detect_main_function(source_path: Path) -> str | None:
    """Detect the main function name in a source file.

    Used for backward compatibility with path = "file.ritz" syntax.
    Returns "main" if found, or None.
    """
    from lexer import Lexer
    from parser import Parser
    import ritz_ast as rast

    try:
        source = source_path.read_text()
        lexer = Lexer(source, str(source_path))
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        module = parser.parse_module()

        for item in module.items:
            if isinstance(item, rast.FnDef) and item.name == 'main':
                return 'main'
        return None
    except Exception:
        return None


def discover_sources(pkg_dir: Path, sources: list[str] | None) -> list[Path]:
    """Discover source files based on sources configuration.

    Per RFC #109 §2.2:
    - Directory entries expand to dir/**/*.ritz
    - Explicit globs are used as-is
    - Exclusion patterns (!path) filter out matching files
    - Default: ["src"] if src/ exists, else ["."]

    Args:
        pkg_dir: Package directory (where ritz.toml is)
        sources: List of source specs, or None for default

    Returns:
        List of .ritz file paths
    """
    import fnmatch

    # Handle default
    if sources is None:
        if (pkg_dir / "src").is_dir():
            sources = ["src"]
        else:
            sources = ["."]

    include_patterns = []
    exclude_patterns = []

    for spec in sources:
        if spec.startswith("!"):
            # Exclusion pattern
            exclude_patterns.append(spec[1:])
        else:
            include_patterns.append(spec)

    # Collect all matching files
    all_files = set()
    for pattern in include_patterns:
        pattern_path = pkg_dir / pattern

        if pattern_path.is_dir():
            # Directory → recursive glob
            for f in pattern_path.rglob("*.ritz"):
                all_files.add(f)
        elif "*" in pattern:
            # Explicit glob pattern
            for f in pkg_dir.glob(pattern):
                if f.is_file() and f.suffix == ".ritz":
                    all_files.add(f)
        else:
            # Single file
            if pattern_path.exists() and pattern_path.suffix == ".ritz":
                all_files.add(pattern_path)

    # Apply exclusions
    result = []
    for f in sorted(all_files):
        excluded = False
        rel_path = str(f.relative_to(pkg_dir))
        for excl in exclude_patterns:
            # Match against relative path
            excl_path = pkg_dir / excl
            if excl_path.is_dir():
                # Exclude entire directory
                if str(f).startswith(str(excl_path)):
                    excluded = True
                    break
            elif fnmatch.fnmatch(rel_path, excl) or fnmatch.fnmatch(rel_path, excl + "/**"):
                excluded = True
                break
        if not excluded:
            result.append(f)

    return result


def get_build_profile(config: dict, profile_name: str | None) -> dict:
    """Get build profile settings.

    Per RFC #109 §2.3:
    - Profiles inherit from [build] section
    - Override with [profile.debug] or [profile.release]
    - Default profile is "debug"

    Returns dict with:
        name: str - profile name
        opt_level: int - optimization level (0-3)
        debug: bool - include debug info
        lto: bool - link-time optimization
    """
    # Defaults
    result = {
        "name": profile_name or "debug",
        "opt_level": 0,
        "debug": True,
        "lto": False,
    }

    # Inherit from [build] section
    if "build" in config:
        build = config["build"]
        if "opt-level" in build:
            result["opt_level"] = build["opt-level"]
        if "debug" in build:
            result["debug"] = build["debug"]
        if "lto" in build:
            result["lto"] = build["lto"]

    # Apply profile-specific overrides
    # When profile_name is None, default to "debug" profile
    effective_profile_name = profile_name or "debug"
    if "profile" in config:
        profile = config["profile"].get(effective_profile_name, {})
        if "opt-level" in profile:
            result["opt_level"] = profile["opt-level"]
        if "debug" in profile:
            result["debug"] = profile["debug"]
        if "lto" in profile:
            result["lto"] = profile["lto"]

    return result


def get_output_dir(pkg_dir: Path, profile: dict) -> Path:
    """Get output directory for a build profile.

    Per RFC #109 §3.1:
    - Debug builds → build/debug/
    - Release builds → build/release/
    """
    return pkg_dir / "build" / profile["name"]


# =============================================================================
# RFC #109 Phase 2: Dependency Resolution and Namespacing
# =============================================================================

# DependencySpec and the [dependencies] resolver live in resolve.py, shared
# with `rz` (AGAST #1835).
from resolve import (  # noqa: E402,F401  (re-exported: tests import them from build)
    DependencySpec, get_transitive_dependencies, package_import_namespaces,
    parse_dependencies)


@dataclass
class BinaryConfig:
    """Complete configuration for a binary target.

    Supports both standard hosted builds and freestanding kernel builds.
    """
    name: str                    # Binary name
    src_path: Path               # Main source file
    additional_sources: list[Path]  # Extra sources (deprecated)
    freestanding: bool = False   # If True, no runtime, custom linker
    target: str = ""             # Target triple (e.g., "x86_64-none-elf")
    target_os: str = ""          # Target OS for conditional compilation (e.g., "harland", "linux")
    linker_script: Path | None = None  # Custom linker script
    asm_files: list[Path] | None = None  # Assembly files to compile
    code_model: str = ""         # LLC code model (e.g., "kernel")
    no_red_zone: bool = False    # Disable red zone (for kernels)
    bin_sources: list[str] | None = None  # Per-binary source directories
    pic: bool = False            # Generate position-independent code (for PIE executables)
    link_runtime: bool = False   # Link with Ritz runtime (_start that calls main and sys_exit)
    main_args: int = 0           # Number of args main() takes (0, 2, or 3) for runtime selection

    def __post_init__(self):
        if self.asm_files is None:
            self.asm_files = []
        if self.bin_sources is None:
            self.bin_sources = []


@dataclass
class LibraryConfig:
    """A [[lib]] target: every module under its sources, and no binary.

    `modules` is what `sources` matched, not what an entry point imports, so a
    module nothing imports is still compiled.
    """
    name: str
    modules: list[Path]


# =============================================================================
# End RFC #109 Phase 2
# =============================================================================


def find_package_at(path: Path) -> tuple[Path, dict] | None:
    """Find a package at the given path (looks for ritz.toml)."""
    path = path.resolve()

    # If path is a file, look in its parent directory
    if path.is_file():
        path = path.parent

    # Look for ritz.toml in this directory
    toml_path = path / "ritz.toml"
    if toml_path.exists():
        with open(toml_path, "rb") as f:
            config = tomllib.load(f)
        return (path, config)

    return None


def find_package_by_name_or_path(name_or_path: str) -> tuple[Path, dict] | None:
    """Find a package by name or path.

    Tries in order:
    1. If it's a path to a directory with ritz.toml, use that
    2. If it's a path to a ritz.toml file, use its directory
    3. Look in current directory for matching subdirectory
    """
    path = Path(name_or_path)

    # Try as direct path
    if path.exists():
        return find_package_at(path)

    # Try as subdirectory of current working directory
    cwd = Path.cwd()
    subdir = cwd / name_or_path
    if subdir.exists():
        return find_package_at(subdir)

    return None


def find_all_packages(search_dir: Path = None) -> list[tuple[Path, dict]]:
    """Find all packages with ritz.toml files under search_dir.

    Defaults to current working directory if not specified.
    """
    if search_dir is None:
        search_dir = Path.cwd()

    search_dir = search_dir.resolve()
    packages = []

    # Search for all ritz.toml files recursively
    for toml_path in sorted(search_dir.glob("**/ritz.toml")):
        with open(toml_path, "rb") as f:
            config = tomllib.load(f)
        packages.append((toml_path.parent, config))

    return packages


def find_packages() -> list[tuple[Path, dict]]:
    """Find all packages - searches from current directory."""
    return find_all_packages()


@dataclass
class SkippedBinary:
    """A declared [[bin]] that this build deliberately does not compile.

    A skip is only legitimate when it is *named*: which target, and why. An
    empty/short binary list must never be inferred to mean "nothing to do" —
    that is how a missing binary passes for a successful build.
    """
    name: str
    reason: str


@dataclass
class BinaryPlan:
    """What plan_binaries() decided about every declared target in a package.

    Four disjoint buckets, and every declared target lands in exactly one:

    - buildable:  binaries to compile; each must produce an artifact
    - libraries:  [[lib]] targets to compile; each must produce an archive
    - skipped:    deliberately not compiled, with a stated reason (success)
    - unresolved: declared as a Ritz target but its source could not be found
                  (failure — a target we were asked for and cannot deliver)
    """
    buildable: list[BinaryConfig]
    skipped: list[SkippedBinary]
    unresolved: list[SkippedBinary]
    libraries: list[LibraryConfig] = field(default_factory=list)


def plan_binaries(pkg_dir: Path, config: dict) -> BinaryPlan:
    """Resolve every declared target into the buckets of a BinaryPlan.

    get_binaries() returns only the buildable bucket, which is all most callers
    need. Anything deciding whether a *package* built must use this instead, so
    that a target dropped during resolution is visibly accounted for rather
    than silently absent from the list.

    A package with neither [[bin]] nor [[lib]] gets one binary named after it,
    from main.ritz under its sources. A package with [[lib]] and no [[bin]] has
    no binary at all (AGAST #1340).
    """
    plan = BinaryPlan(buildable=[], skipped=[], unresolved=[])
    binaries = plan.buildable

    # Check if this is a test-only package
    is_test_only = config.get("build", {}).get("test_only", False)
    if is_test_only:
        return plan  # Test-only packages have no binaries

    # Get package-level sources configuration (RFC #109)
    # Check top-level, [package], and [build] sections (TOML puts keys in current section)
    pkg_sources = config.get("sources")
    if pkg_sources is None:
        pkg_sources = config.get("package", {}).get("sources")
    if pkg_sources is None:
        pkg_sources = config.get("build", {}).get("sources")
    if pkg_sources is None:
        pkg_sources = ["src"]  # Default
    if isinstance(pkg_sources, str):
        pkg_sources = [pkg_sources]

    # [[lib]] sections. `sources` overrides the package's, as it does for
    # [[bin]]: zeus's package sources include test/, which is not library code.
    for lib_entry in config.get("lib", []):
        lib_sources = lib_entry.get("sources", pkg_sources)
        if isinstance(lib_sources, str):
            lib_sources = [lib_sources]
        modules = discover_sources(pkg_dir, lib_sources)
        if modules:
            plan.libraries.append(LibraryConfig(lib_entry["name"], modules))
        else:
            # A library that compiles nothing must not pass for a built one.
            plan.unresolved.append(SkippedBinary(
                lib_entry["name"], f"[[lib]] has no .ritz modules under {lib_sources}"))

    # Check for [[bin]] sections
    if "bin" in config:
        for bin_entry in config["bin"]:
            name = bin_entry["name"]

            # RFC #109: entry = "module::function"
            if "entry" in bin_entry:
                entry = bin_entry["entry"]
                # Use bin-specific sources if provided, else package-level
                bin_sources_list = bin_entry.get("sources", pkg_sources)
                if isinstance(bin_sources_list, str):
                    bin_sources_list = [bin_sources_list]
                result = resolve_entry_point(entry, pkg_dir, bin_sources_list)
                if result is None:
                    # Not a skip: the package declares a Ritz binary whose
                    # source we cannot find. Record it as unresolved so the
                    # package build fails instead of quietly building N-1.
                    print(f"  ⚠ Could not resolve entry point: {entry}", file=sys.stderr)
                    plan.unresolved.append(SkippedBinary(
                        name, f"could not resolve entry point '{entry}'"))
                    continue
                src_path, _fn_name = result
            # Legacy: path = "src/main.ritz"
            elif "path" in bin_entry:
                src_path = pkg_dir / bin_entry["path"]
                # Legitimate skip: a [[bin]] pointing at a .py/.sh script is
                # not something this compiler builds. Named, not inferred.
                if not src_path.suffix == ".ritz":
                    plan.skipped.append(SkippedBinary(
                        name, f"not a Ritz source ({src_path.name})"))
                    continue
            # Default: src/{name}.ritz
            else:
                src_path = pkg_dir / "src" / f"{name}.ritz"

            # Get additional sources if specified (legacy, deprecated)
            additional_sources = []
            if "sources" in bin_entry and isinstance(bin_entry["sources"], list):
                # Check if these are paths or directory specs
                for src in bin_entry["sources"]:
                    src_path_check = pkg_dir / src
                    if src_path_check.is_file():
                        additional_sources.append(src_path_check)

            # Parse freestanding build options
            freestanding = bin_entry.get("freestanding", False)
            target = bin_entry.get("target", "")
            target_os = bin_entry.get("target_os", "")

            # Parse [bin.NAME.linker] section
            # TOML puts [bin.harland.linker] as bin_entry["harland"]["linker"]
            nested_config = bin_entry.get(name, {})
            linker_config = nested_config.get("linker", {})
            linker_script = None
            if linker_config.get("script"):
                linker_script = pkg_dir / linker_config["script"]

            # Parse [bin.NAME.asm] section
            asm_config = nested_config.get("asm", {})
            asm_files = []
            for asm_file in asm_config.get("files", []):
                asm_files.append(pkg_dir / asm_file)

            # Parse [bin.NAME.flags] section
            flags_config = nested_config.get("flags", {})
            code_model = flags_config.get("code-model", "")
            no_red_zone = flags_config.get("no-red-zone", False)
            pic = flags_config.get("pic", False)

            # Parse runtime linking options
            # link_runtime: bool - link with Ritz runtime (_start)
            # main_args: int - number of args main() takes (0, 2, or 3)
            link_runtime = bin_entry.get("link_runtime", False)
            main_args = bin_entry.get("main_args", 0)

            # Per-binary source directories
            bin_sources = bin_entry.get("sources", [])
            if isinstance(bin_sources, str):
                bin_sources = [bin_sources]

            binaries.append(BinaryConfig(
                name=name,
                src_path=src_path,
                additional_sources=additional_sources,
                freestanding=freestanding,
                target=target,
                target_os=target_os,
                linker_script=linker_script,
                asm_files=asm_files,
                code_model=code_model,
                no_red_zone=no_red_zone,
                bin_sources=bin_sources,
                pic=pic,
                link_runtime=link_runtime,
                main_args=main_args,
            ))
    elif "lib" not in config:
        # Default: single binary with package name
        name = config["package"]["name"]
        result = resolve_entry_point("main::main", pkg_dir, pkg_sources)
        if result is None:
            plan.unresolved.append(SkippedBinary(
                name, f"no main.ritz under sources {pkg_sources}; "
                      "declare a [[bin]] or a [[lib]]"))
        else:
            binaries.append(BinaryConfig(
                name=name,
                src_path=result[0],
                additional_sources=[],
            ))

    return plan


def get_binaries(pkg_dir: Path, config: dict) -> list[BinaryConfig]:
    """Get list of BinaryConfig objects for all buildable binary targets.

    Returns empty list for test-only packages (no binary to build).

    Supports both RFC #109 syntax and legacy syntax:
    - RFC #109: entry = "module::main"  → resolves to src/module.ritz
    - Legacy:   path = "src/main.ritz"  → direct file path

    Also supports freestanding builds with:
    - freestanding = true
    - target = "x86_64-none-elf"
    - [bin.NAME.linker] script = "linker.ld"
    - [bin.NAME.asm] files = ["boot.s", "isr.s"]
    - [bin.NAME.flags] code-model = "kernel", no-red-zone = true

    NOTE: this is a lossy view — targets that were skipped or failed to resolve
    are simply absent. Use plan_binaries() when the difference matters.
    """
    return plan_binaries(pkg_dir, config).buildable


def ritz1_compile_cmd(compiler: str, src: Path, ll_path: Path) -> Optional[list]:
    """The ritz1-family command that compiles one source to LLVM IR.

    ritz1's CLI is minimal: <input> -o <output> [-I <ritz_path>]
    [--target-os <os>]. It doesn't understand --no-runtime, --deps, --sources
    or --project-root; callers append --target-os when they need it.
    Its default emitter is non-freestanding (no _start embedded), so the
    "--no-runtime" semantics come for free. Import resolution: ritz1 tries
    source_dir first, then RITZ_PATH (see `ritz1_env`). `-I` points at the ritz
    ROOT so ritzlib/* imports resolve.

    Returns None (after saying why) if the binary is missing.
    """
    ritz1_bin, make_hint = RITZ1_FAMILY_BINS[compiler]
    if not ritz1_bin.exists():
        print(f"  ✗ {compiler} binary not found at {ritz1_bin}", file=sys.stderr)
        print(f"    Run: cd {ROOT} && {make_hint}", file=sys.stderr)
        return None
    return [str(ritz1_bin), str(src), "-o", str(ll_path), "-I", str(ROOT)]


def ritz1_env(namespaces: dict | None = None) -> dict:
    """Environment for a ritz1-family compile.

    ritz1 needs RITZ_PATH to resolve qualified `ritzlib.*` imports AND
    cross-project imports (`zeus.shm`, `mausoleum.client`). ROOT
    (projects/ritz) lets ritz1 find ritzlib/* and self-host modules;
    ROOT.parent (projects/) lets the subdir-probe resolver find cross-project
    imports like `zeus.shm` → `projects/zeus/lib/shm.ritz`. Any caller-provided
    RITZ_PATH (e.g. `./rz` pre-building a list of workspace roots) is kept,
    after those two. Colon-separated, gcc-style.

    `namespaces` (from `package_import_namespaces`) covers what ritz1's
    minimal CLI can't take as --deps: for each namespace whose directory is
    named after it, the directory's parent is appended, so ritz1's
    `<entry>/<pkg>/{lib,src}/...` probe finds it — including a package
    importing itself by name from outside projects/ (AGAST #1538). They go
    ahead of projects/, so a declared dependency outranks a workspace project
    of its name: examples/test_deps/app's `squeeze` is not projects/squeeze,
    and ritz1 compiled its `import squeeze.gzip` against the latter, leaving
    the calls it lacked to the link (AGAST #3255, which refuses them now).
    Every workspace package's dependencies live in projects/ already, so this
    reorders nothing for them.
    """
    env = os.environ.copy()
    entries = [str(ROOT)]
    for name, spec in (namespaces or {}).items():
        if spec.path.name == name and str(spec.path.parent) not in entries:
            entries.append(str(spec.path.parent))
    for e in [str(ROOT.parent), *env.get("RITZ_PATH", "").split(os.pathsep)]:
        if e and e not in entries:
            entries.append(e)
    env["RITZ_PATH"] = os.pathsep.join(entries)
    return env


# ---------------------------------------------------------------------------
# AGAST #1382: binary provenance.
#
# The only question the project-level fast path may ask is "was THIS binary
# produced from THESE sources by THIS compiler with THIS link profile?".
# Nothing answered that before: the fast path forgave any source whose mtime
# was `<=` the binary's (so a same-second edit, `cp -p`, `tar -x` or a git
# checkout served a stale binary), and for newer sources it consulted the
# source's own `.ritz.sig` -- which describes the SOURCE, not the binary, and
# is shared by ritz0 and ritz1 (both write it; see ritz0/ritz0.py).
#
# So each link writes `<name>.manifest.json` next to the binary, recording
# the content hash of every source it was built from (in link order), the
# compiler name and hash, the link-relevant profile keys, and the binary's
# own hash. The fast path recomputes that record and compares. mtime is not
# an input at all: sha256 over a package's sources costs milliseconds, which
# is noise next to a ritz0/ritz1 invocation.
# ---------------------------------------------------------------------------

BINARY_MANIFEST_VERSION = 1
_PROFILE_LINK_KEYS = ("opt_level", "debug", "lto")


def binary_manifest_path(bin_path: Path) -> Path:
    """`build/<profile>/<name>` -> `build/<profile>/<name>.manifest.json`."""
    return bin_path.with_name(bin_path.name + ".manifest.json")


def _sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def binary_provenance(sources: list[Path], compiler: str, compiler_hash: str, profile: dict,
                      runtime: list[Path] = ()) -> dict:
    """What a binary linked right now from `sources` would be built from.

    `runtime` lists the `_start` shim sources (`runtime/*.ll`) the link may
    pull in; they are not Ritz sources and not part of the compiler hash, so
    they are recorded separately.

    Hash the sources BEFORE compiling them: if one is edited mid-build, the
    manifest records the pre-edit content and the next build sees a
    mismatch and rebuilds. That's the safe direction. Raises OSError if a
    source is unreadable.
    """
    return {
        "version": BINARY_MANIFEST_VERSION,
        "compiler": compiler,
        "compiler_hash": compiler_hash,
        "profile": {k: profile.get(k) for k in _PROFILE_LINK_KEYS},
        "sources": [[str(Path(s).resolve()), _sha256_file(Path(s))] for s in sources],
        "runtime": [[str(Path(r).resolve()), _sha256_file(Path(r))] for r in runtime],
    }


def private_output_path(path: Path) -> Path:
    """A temp name next to `path`, unique to this call.

    AGAST #1499: two builds can write one output path (worktrees or overlay
    roots that reach a package through a symlink). A fixed `<name>.tmp`
    lets one build rename the other's half-written file, or fail on a temp
    the other already renamed. Same directory, so `os.replace` is atomic.
    """
    return path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:12]}.tmp")


def write_binary_manifest(bin_path: Path, provenance: dict,
                          binary_sha256: Optional[str] = None) -> None:
    """Record that the binary with sha256 `binary_sha256` came from
    `provenance`. Without it, hash `bin_path` as it is on disk now, which is
    only right when nothing else can write that path (see publish_binary)."""
    import json
    if binary_sha256 is None:
        binary_sha256 = _sha256_file(bin_path)
    record = dict(provenance, binary_sha256=binary_sha256)
    manifest = binary_manifest_path(bin_path)
    tmp = private_output_path(manifest)
    try:
        tmp.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        os.replace(tmp, manifest)
    finally:
        tmp.unlink(missing_ok=True)


def publish_binary(built: Path, bin_path: Path, provenance: Optional[dict]) -> None:
    """Move the file this build produced (`built`, from private_output_path)
    to `bin_path` and record its provenance.

    AGAST #1499: the hash is taken from `built` before it becomes visible.
    Hashing `bin_path` afterwards would certify whatever another build wrote
    there in between as built from THIS build's sources, and every later
    cached build would serve it. With our own hash, a foreign binary at
    `bin_path` never matches the manifest, so the next build relinks.
    """
    digest = _sha256_file(built)
    os.replace(built, bin_path)
    if provenance is not None:
        write_binary_manifest(bin_path, provenance, binary_sha256=digest)


def binary_is_up_to_date(bin_path: Path, provenance: dict) -> bool:
    """True only if `bin_path`'s manifest proves it was built from `provenance`.

    Every doubt is a rebuild: missing/corrupt manifest, missing binary, a
    binary rewritten by something that did not update the manifest, or an
    unidentifiable compiler (`compute_compiler_hash` failed -> "unknown").
    """
    import json
    if provenance.get("compiler_hash") in (None, "", "unknown"):
        return False
    try:
        recorded = json.loads(binary_manifest_path(bin_path).read_text())
        if not isinstance(recorded, dict):
            return False
        if recorded.pop("binary_sha256", None) != _sha256_file(bin_path):
            return False
    except (OSError, ValueError):
        return False
    return recorded == provenance


@dataclass(frozen=True)
class Target:
    """What a module's object is compiled for (AGAST #1835).

    The per-module stages (discover, emit, verify, `clang -c`, store) are the
    same for every binary; a Target holds what differs between a hosted
    binary and a freestanding one (kernel, bootloader, UEFI app). It replaced
    compile_freestanding_binary's own copy of those stages, which had drifted:
    no compile_ll_to_obj (so no timeout or memory cap), and a return on the
    first clang failure.

    `clang_flags` are a freestanding target's object flags after `-c`;
    `target_os` selects [[target_os = "..."]] code in the compiler.
    """
    freestanding: bool = False
    clang_flags: Tuple[str, ...] = ()
    target_os: str = ""

    @property
    def obj_flags(self) -> List[str]:
        """The flags compile_ll_to_obj runs clang with."""
        if not self.freestanding:
            return OBJ_CLANG_FLAGS
        return ["-c", *self.clang_flags]

    @property
    def key_flags(self) -> Optional[dict]:
        """cas_module_key's `object_flags`: None for the hosted defaults.
        Unchanged from AGAST #1896, so existing store entries stay valid."""
        if not self.freestanding:
            return None
        return {"freestanding": True, "target_os": self.target_os,
                "clang": list(self.clang_flags)}

    def compiler_args(self) -> List[str]:
        """Arguments the compiler (ritz0 or ritz1) takes for this target."""
        return ["--target-os", self.target_os] if self.target_os else []


HOSTED = Target()


def _deps_json(dependencies: Optional[dict[str, DependencySpec]]) -> str:
    return json.dumps({name: {"path": str(spec.path), "sources": spec.sources}
                       for name, spec in dependencies.items()})


def discover_modules(src_path: Path, *, project_root: Path,
                     dependencies: dict[str, DependencySpec] = None,
                     source_roots: list[str] = None) -> Optional[list[Path]]:
    """Every module `src_path` imports, transitively, imports first and
    `src_path` last (ritz0/list_deps.py, in a subprocess). None once an
    import resolution failure has been reported."""
    cmd = [sys.executable, str(RITZ0_DIR / "list_deps.py"), str(src_path),
           "--project-root", str(project_root)]
    if dependencies:
        cmd.extend(["--deps", _deps_json(dependencies)])
    if source_roots:
        cmd.extend(["--sources", json.dumps(source_roots)])
    # The environment carries RITZ_PATH for import resolution.
    result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ)
    if result.returncode != 0:
        print(f"  ✗ import resolution failed: {result.stderr}", file=sys.stderr)
        return None
    return [Path(f.strip()) for f in result.stdout.strip().split('\n') if f.strip()]


def module_compile_cmd(compiler: str, src: Path, ll_path: Path, target: Target, *,
                       dependencies: dict[str, DependencySpec] = None,
                       source_roots: list[str] = None,
                       pkg_dir: Path = None) -> Optional[list]:
    """The command that emits `src`'s IR to `ll_path` with no runtime.
    None when the ritz1-family compiler cannot be used (already reported)."""
    if compiler.startswith("ritz1"):
        # ritz1 emits no _start by default, which is what --no-runtime asks
        # of ritz0.
        cmd = ritz1_compile_cmd(compiler, src, ll_path)
        if cmd is None:
            return None
    else:
        cmd = [sys.executable, str(RITZ0), str(src), "-o", str(ll_path), "--no-runtime"]
        # Pass dependencies if any (RFC #109 Phase 2)
        if dependencies:
            cmd.extend(["--deps", _deps_json(dependencies)])
        # Pass source roots if any (for import resolution)
        if source_roots:
            cmd.extend(["--sources", json.dumps(source_roots)])
        # Pass project root (package directory) for source root resolution
        if pkg_dir:
            cmd.extend(["--project-root", str(pkg_dir)])
    return cmd + target.compiler_args()


def compile_modules(sources: list[Path], artifact_dir: Path, *, cache, store, use_cache: bool,
                    compiler: str, dependencies: dict[str, DependencySpec] = None,
                    source_roots: list[str] = None, pkg_dir: Path = None,
                    target: Target = HOSTED) -> Optional[list[Path]]:
    """Compile each source to a `target` object in `artifact_dir`, through
    the store.

    All sources are compiled with --no-runtime; a binary gets _start from the
    runtime .o at link time. Every source is attempted, so one run reports
    every broken module (AGAST #1286), whether the compiler or clang rejects
    it. `source_roots` and `pkg_dir` are passed to ritz0 as given (`pkg_dir`
    as --project-root; a freestanding build passes absolute roots and none).

    Returns the objects in source order, or None once the failures have been
    reported.
    """
    link_files = []
    compile_failures: List[Tuple[Path, str]] = []
    obj_failures: List[str] = []  # AGAST #1731
    for src in sources:
        # Use a unique name to avoid collisions (e.g., multiple sys.ritz)
        # Hash the full path to get a unique identifier
        path_hash = hashlib.md5(str(src).encode()).hexdigest()[:8]
        src_name = f"{src.stem}_{path_hash}"
        ll_path = artifact_dir / f"{src_name}.ll"
        bc_path = artifact_dir / f"{src_name}.bc"
        obj_path = artifact_dir / f"{src_name}.o"

        # AGAST #1808: the shared content-addressed store. A hit is an
        # object compiled from exactly this source and import closure, by
        # this compiler, with these flags: in this worktree or any other.
        # It replaces the per-worktree .ritz-cache objects (and the
        # .bc/.ll tiers, which a hit on the .o always made unreachable).
        cas_key = (cas_module_key(src, cache, compiler, target.key_flags)
                   if use_cache else None)

        def compile_src(src=src, ll_path=ll_path, obj_path=obj_path) -> Optional[tuple]:
            """Emit, verify and `clang -c` one module into obj_path.
            None on success, else ("compile" | "obj" | "no-compiler", msg)."""
            compile_cmd = module_compile_cmd(
                compiler, src, ll_path, target, dependencies=dependencies,
                source_roots=source_roots, pkg_dir=pkg_dir)
            if compile_cmd is None:
                return ("no-compiler", "")

            env = ritz1_env(dependencies) if compiler.startswith("ritz1") else os.environ.copy()
            result = subprocess.run(compile_cmd, capture_output=True, text=True, env=env)
            if result.returncode != 0:
                return ("compile", result.stderr)
            relay_compiler_warnings(result.stderr)

            # AGAST #1308: verify before clang, and before the .ll is cached.
            # Caching invalid IR would make the bug survive a rebuild and then
            # reappear on a machine whose clang is stricter, which is exactly
            # the failure mode this is here to kill.
            ir_error = verify_ir(ll_path, src)
            if ir_error is not None:
                return ("compile", ir_error)

            # AGAST #192: Pre-compile freshly emitted .ll to .o.  Without
            # this, the link step pays for full IR lowering on every file
            # (cached or not).  Caching the .o means subsequent rebuilds —
            # even ones that re-invoke ritz1 — skip clang's slow path.
            #
            # AGAST #1731: there is deliberately no .bc / .ll fallback here.
            # One used to swallow a failed (or capped) -O2 compile and link the
            # .ll instead, which hid #1730 for a whole gate.
            obj_error = compile_ll_to_obj(ll_path, obj_path, src, target.obj_flags)
            if obj_error is not None:
                return ("obj", obj_error)
            return None

        if cas_key is None:
            failure = compile_src()
        else:
            def build_fn(compile_src=compile_src, ll_path=ll_path, obj_path=obj_path):
                failure = compile_src()
                if failure is not None:
                    raise cas.BuildFailed(failure)
                return {"ll": ll_path, "o": obj_path}
            # AGAST #1911: single-flight. A hit, or a key another
            # process is compiling right now, is copied; only a caller
            # that still misses under the key's lock compiles.
            ident = cas.module_identity(src)
            try:
                # AGAST #2794: fetch, so a hit gc'd before the copy rebuilds.
                meta = {"module": ident, "compiler": compiler}
                if target.freestanding:
                    meta["freestanding"] = target.key_flags
                store.fetch(cas_key, "o", build_fn, obj_path, identity=ident, meta=meta)
                failure = None
            except cas.BuildFailed as e:
                failure = e.args[0]

        if failure is not None:
            kind, msg = failure
            if kind == "no-compiler":
                return None
            if kind == "obj":
                obj_failures.append(msg)
            else:
                # AGAST #1286: collect and keep going so every broken file is
                # reported, not just whichever one happened to be compiled
                # first. Checked after the loop, before linking.
                compile_failures.append((src, msg))
            continue
        link_files.append(obj_path)

    # AGAST #1286: every source has now been attempted. If any failed,
    # report them all and stop before linking — linking a partial set of
    # objects would only produce confusing undefined-symbol errors on top
    # of the real diagnostics.
    if compile_failures or obj_failures:
        report_compile_failures(compile_failures, compiler)
        report_obj_failures(obj_failures)
        return None
    return link_files


def link_hosted(bin_path: Path, runtime_obj: Path, link_files: list[Path],
                profile: dict) -> bool:
    """Link a hosted binary: the runtime `_start` object, then the module
    objects, with clang (gcc if absent) and the profile's options. False
    once a failure has been reported."""
    # Use -g to preserve DWARF debug info, -nostdlib for bare-metal
    print(f"  ⚡ Linking {len(link_files)} object files...")
    if os.environ.get("RITZ_DEBUG"):
        for lf in link_files:
            print(f"    - {lf}")
    # Try clang first, fall back to gcc
    if shutil.which("clang"):
        linker_name = "clang"
    elif shutil.which("gcc"):
        linker_name = "gcc"
    else:
        print(f"  ✗ Neither clang nor gcc found in PATH", file=sys.stderr)
        return False

    # Link: runtime.o + all objects -> binary, with profile-specific options.
    # -march=native enables CPU-specific features (SHA-NI, AES-NI, etc.) for code generation
    # -msha matches the per-object compile flag
    link_cmd = [linker_name, str(runtime_obj), *[str(f) for f in link_files],
                "-o", str(bin_path), "-nostdlib", "-march=native", "-msha",
                f"-O{profile.get('opt_level', 0)}"]
    if profile.get("debug", True):
        link_cmd.append("-g")
    if profile.get("lto", False):
        link_cmd.append("-flto")

    if os.environ.get("RITZ_DEBUG"):
        print(f"  [DEBUG] Link cmd: {' '.join(link_cmd[:5])}... ({len(link_files)} files)")
        print(f"  [DEBUG] Full command: {' '.join(link_cmd)}")

    result = subprocess.run(link_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ {linker_name} linking failed: {result.stderr}", file=sys.stderr)
        return False
    return True


def compile_binary(name: str, src_path: Path, out_dir: Path, additional_sources: list[Path] = None, keep_artifacts: bool = False, use_cache: bool = True, profile: dict = None, dependencies: dict[str, DependencySpec] = None, pkg_dir: Path = None, source_roots: list[str] = None, compiler: str = "ritz0", on_rebuild=None) -> Path:
    """Compile Ritz source file(s) to a binary.

    Args:
        name: Name of the output binary
        src_path: Main source file (entry point with main())
        out_dir: Directory to place the binary
        additional_sources: Additional .ritz files to compile and link (deprecated, use imports)
        keep_artifacts: If True, keep .ll files in build/ for debugging
        use_cache: If True, use build cache to skip unchanged files
        profile: Build profile dict with opt_level, debug, lto settings (RFC #109)
        dependencies: RFC #109 dependency specs for namespace resolution
        pkg_dir: Package directory for project root (defaults to ROOT for standalone builds)
        source_roots: List of source directories to search for imports (e.g., ["src", "kernel/src"])
        on_rebuild: Optional zero-arg callable, invoked once just before real
            compile/link work starts. NOT invoked when the binary is proven up
            to date (AGAST #1382), so the caller can tell "rebuilt" from
            "already up to date" and never report work it did not do.

    Uses separate compilation model:
    1. Discover all source files via import resolution
    2. Compile each source file to .ll (functions from current file: define, imports: declare)
    3. Convert .ll to .bc (bitcode) for faster linking (RFC #109 Phase 3)
    4. Link all .bc files together with clang/gcc

    Uses gcc for linking when clang is not available.
    """

    # Default profile if not specified
    if profile is None:
        profile = {"name": "debug", "opt_level": 0, "debug": True, "lto": False}
    bin_path = out_dir / name

    # The build cache (namespaced per compiler) holds the import scans that
    # key each module in the CAS, and the compiler fingerprint.
    cache = get_build_cache(compiler)

    # If the compiler differs from the one the cache last recorded (ritz0
    # source edited, ritz1 binary rebuilt, etc.), drop the import scans.
    # See `BuildCache.invalidate_if_compiler_changed`.
    #
    # We also remember the verdict locally: if the compiler changed, the
    # already-linked `bin_path` is stale too (it was linked from objects
    # the previous compiler produced), so the project-level fast path below
    # must NOT return it. The fast path only re-uses `bin_path` when the
    # compiler is unchanged.
    compiler_changed = cache.invalidate_if_compiler_changed() if use_cache else False

    # AGAST #1808: compiled modules come from, and go to, the shared store.
    store = cas.ArtifactStore()

    # Pass the package directory as project root (fallback to ritz ROOT for
    # standalone builds), so ritzlib resolves the same way for every
    # dependency.
    project_root = pkg_dir if pkg_dir else ROOT
    # AGAST #1832: the per-module cache must resolve imports exactly as
    # list_deps does, or modules found via source roots / dependency
    # namespaces drop out of its import graph.
    cache.set_import_context(
        project_root=project_root,
        dependencies={n: (s.path, s.sources) for n, s in (dependencies or {}).items()},
        source_roots=source_roots,
    )
    all_sources = discover_modules(src_path, project_root=project_root,
                                   dependencies=dependencies, source_roots=source_roots)
    if all_sources is None:
        return None

    # Add any explicit additional sources (for backwards compatibility)
    if additional_sources:
        for src in additional_sources:
            if src not in all_sources:
                all_sources.insert(-1, src)  # Insert before main

    # AGAST #192 / #1382: project-level fast path. Skip emit/link entirely
    # only when the binary's manifest proves it was built from exactly the
    # current content of every transitive source, by the current compiler
    # (name + hash: editing a ritz0 codegen file or rebuilding ritz1 changes
    # it), with the current link profile. See `binary_is_up_to_date`.
    #
    # mtime is deliberately NOT consulted: `<=` forgave same-second edits and
    # older-mtime restores (cp -p, tar -x, git ops), and the `.ritz.sig`
    # next to each source answers a question about the source, not about
    # this binary. A bare `touch` still hits the fast path because content
    # is what's compared. `use_cache` gates it so debug runs always rebuild.
    try:
        provenance = binary_provenance(
            all_sources, compiler, cache._get_current_compiler_hash(), profile,
            runtime=[ll for o in (RITZ_START_NOARGS, RITZ_START, RITZ_START_ENVP)
                     if (ll := o.with_suffix(".ll")).exists()])
    except OSError:
        provenance = None
    if (use_cache and provenance is not None and not compiler_changed
            and binary_is_up_to_date(bin_path, provenance)):
        return bin_path

    # No need to delete the old manifest here: it records the binary's own
    # sha256, so a failed or interrupted link that disturbs `bin_path` can
    # never match it, and a build that fails before linking leaves the old
    # binary/manifest pair consistent.
    if on_rebuild is not None:
        on_rebuild()

    # Use build/ directory for artifacts if keeping them, otherwise temp
    if keep_artifacts:
        artifact_dir = ROOT / "build"
        artifact_dir.mkdir(exist_ok=True)
    else:
        artifact_dir = Path(tempfile.mkdtemp())

    # Detect main's signature to choose the right runtime
    main_params = detect_main_signature(src_path)
    runtime_obj = get_runtime_object(main_params)

    # Build the runtime object on demand — it is derived from a tracked .ll.
    if not ensure_runtime_object(runtime_obj):
        return None

    try:
        link_files = compile_modules(
            all_sources, artifact_dir, cache=cache, store=store, use_cache=use_cache,
            compiler=compiler, dependencies=dependencies, source_roots=source_roots,
            pkg_dir=pkg_dir)
        if link_files is None:
            return None

        # Link to a private name, then publish it with its own hash (#1499).
        linked = private_output_path(bin_path)
        try:
            if not link_hosted(linked, runtime_obj, link_files, profile):
                return None
            publish_binary(linked, bin_path, provenance)
        finally:
            linked.unlink(missing_ok=True)
        return bin_path
    finally:
        # Clean up temp directory if not keeping artifacts
        # Disable cleanup temporarily for debugging
        if os.environ.get("RITZ_KEEP_TEMP"):
            print(f"  [DEBUG] Keeping temp dir: {artifact_dir}")
        elif not keep_artifacts and artifact_dir.exists():
            shutil.rmtree(artifact_dir, ignore_errors=True)


# AGAST #2141: exit code for "every failure was a missing toolchain binary".
# The room gate runs `rz build --all`; on a machine without lld-link, harland's
# UEFI loader cannot link. Exit 1 there would read as a regression, and
# excusing it would read as a pass -- it is neither, so it gets its own code.
EXIT_SETUP = 3

# Targets in this process that failed only because a tool is absent:
# target name -> tool. build_package() moves each into its result.
_SETUP_MISSES: dict[str, str] = {}


def record_setup_miss(target: str, tool: str) -> None:
    """Mark `target`'s failure as the environment's fault (missing `tool`)."""
    _SETUP_MISSES[target] = tool


def find_llvm_tool(name: str) -> str:
    """Find LLVM tool, trying versioned names."""
    import shutil as shutil_mod
    # For lld, prefer ld.lld over the generic wrapper, fall back to GNU ld
    if name == "lld":
        if shutil_mod.which("ld.lld"):
            return "ld.lld"
        for ver in ["20", "19", "18", "17", "16", "15"]:
            if shutil_mod.which(f"ld.lld-{ver}"):
                return f"ld.lld-{ver}"
        # Fall back to GNU ld if LLD is not available
        if shutil_mod.which("ld"):
            return "ld"
    # Try unversioned first
    if shutil_mod.which(name):
        return name
    # Try common version suffixes
    for ver in ["20", "19", "18", "17", "16", "15", "14"]:
        versioned = f"{name}-{ver}"
        if shutil_mod.which(versioned):
            return versioned
    # Not found
    return name  # Will fail later with helpful error


def compile_library(lib: LibraryConfig, out_dir: Path, *, keep_artifacts: bool = False,
                    use_cache: bool = True, dependencies: dict[str, DependencySpec] = None,
                    pkg_dir: Path = None, source_roots: list[str] = None,
                    compiler: str = "ritz0", on_rebuild=None) -> Optional[Path]:
    """Compile a [[lib]] into `out_dir/lib<name>.a`. None on failure.

    The archive holds this package's modules only. A module's imports are
    compiled by whichever binary links them, so the archive's undefined
    symbols are its dependencies, as for any static library.

    `on_rebuild` is as for compile_binary (AGAST #1382): not invoked when the
    archive is proven up to date.
    """
    archive = out_dir / f"lib{lib.name}.a"
    cache = get_build_cache(compiler)
    compiler_changed = cache.invalidate_if_compiler_changed() if use_cache else False
    store = cas.ArtifactStore()
    cache.set_import_context(
        project_root=pkg_dir if pkg_dir else ROOT,
        dependencies={n: (s.path, s.sources) for n, s in (dependencies or {}).items()},
        source_roots=source_roots,
    )

    # A module's store key covers its source, its import closure, the compiler
    # and the object flags, so equal keys prove equal objects. Keys go in the
    # manifest instead of file hashes because no entry point names the closure.
    # None means the module could not be scanned; the compile reports why.
    provenance = None
    if use_cache:
        keys = [cas_module_key(module, cache, compiler) for module in lib.modules]
        if None not in keys:
            provenance = {
                "version": BINARY_MANIFEST_VERSION,
                "compiler": compiler,
                "compiler_hash": cache._get_current_compiler_hash(),
                "modules": [[str(m.resolve()), k] for m, k in zip(lib.modules, keys)],
            }
    if (provenance is not None and not compiler_changed
            and binary_is_up_to_date(archive, provenance)):
        return archive

    if on_rebuild is not None:
        on_rebuild()

    artifact_dir = ROOT / "build" if keep_artifacts else Path(tempfile.mkdtemp())
    artifact_dir.mkdir(exist_ok=True)
    try:
        objects = compile_modules(
            lib.modules, artifact_dir, cache=cache, store=store, use_cache=use_cache,
            compiler=compiler, dependencies=dependencies, source_roots=source_roots,
            pkg_dir=pkg_dir)
        if objects is None:
            return None

        archiver = shutil.which(find_llvm_tool("llvm-ar")) or shutil.which("ar")
        if archiver is None:
            record_setup_miss(f"lib{lib.name}", "llvm-ar or ar")
            print("  ✗ Neither llvm-ar nor ar found in PATH", file=sys.stderr)
            return None

        # A fresh archive, then a rename: `ar r` into the old one would keep
        # the members of modules that have since been deleted.
        # A private name, so concurrent builds never share it (#1499).
        tmp_archive = private_output_path(archive)
        try:
            result = subprocess.run(
                [archiver, "rcs", str(tmp_archive)] + [str(o) for o in objects],
                capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  ✗ {archiver} failed: {result.stderr}", file=sys.stderr)
                return None
            publish_binary(tmp_archive, archive, provenance)
        finally:
            tmp_archive.unlink(missing_ok=True)
        return archive
    finally:
        if not keep_artifacts:
            shutil.rmtree(artifact_dir, ignore_errors=True)


def freestanding_target(bin_config: BinaryConfig) -> Target:
    """The Target a freestanding [[bin]] compiles its modules for.

    Its object flags are its own (no -O2, a --target triple), so its objects
    never share a store entry with a hosted build of the same source.
    """
    target = bin_config.target or "x86_64-none-elf"
    if "uefi" in target.lower():
        # UEFI: compile for Windows x64 ABI (produces COFF objects for lld-link)
        clang_flags = [
            "--target=x86_64-unknown-windows-gnu",  # Windows x64 target for COFF
            "-fshort-wchar",      # UEFI uses 16-bit wchar
            "-mno-red-zone",      # Required for UEFI
            "-fno-stack-protector",
            "-ffreestanding",
        ]
    else:
        clang_flags = [
            f"--target={target}",
            *FREESTANDING_FLAGS,
            "-march=native",  # Enable CPU-specific features (SHA-NI, AES-NI, etc.)
            "-msha",  # Force SHA extensions: code using the SHA-NI
                      # intrinsics (e.g. cryptosec's test_sha_ni.ritz) must
                      # compile even where it never runs. Without this,
                      # clang refuses to lower llvm.x86.sha256rnds2 on hosts
                      # where -march=native doesn't include +sha (e.g.
                      # pre-Skylake).
        ]
        # Add PIC flag if explicitly requested or for Linux targets
        if bin_config.pic or target.endswith("-linux"):
            clang_flags.append("-fPIC")
        # Note: -mcmodel=large is incompatible with -fPIC on x86_64. For PIC
        # code the default small model (GOT/PLT relocations) is used instead.
        if bin_config.code_model and not (bin_config.pic and bin_config.code_model == "large"):
            clang_flags.append(f"-mcmodel={bin_config.code_model}")
        if bin_config.no_red_zone:
            clang_flags.append("-mno-red-zone")
    return Target(freestanding=True, clang_flags=tuple(clang_flags),
                  target_os=bin_config.target_os or "")


_INCBIN = re.compile(r'\.incbin\s+"([^"]+)"')


def assemble_objects(asm_files: list[Path], pkg_dir: Path,
                     artifact_dir: Path) -> Optional[list[Path]]:
    """Assemble a freestanding [[bin]]'s .s files. None once a failure has
    been reported. A missing file, or one that .incbin's a file not built
    yet (user_elf.s), is skipped with a warning."""
    objects = []
    print(f"  Assembling {len(asm_files)} assembly file(s)...")
    for asm_file in asm_files:
        if not asm_file.exists():
            print(f"  ⚠ Assembly file not found: {asm_file}")
            continue

        missing = next((m.group(1) for line in asm_file.read_text().split('\n')
                        if '.incbin' in line and (m := _INCBIN.search(line))
                        and not (pkg_dir / m.group(1)).exists()), None)
        if missing is not None:
            print(f"  ⚠ Skipping {asm_file.name}: missing {missing}")
            continue

        obj_path = artifact_dir / f"{asm_file.stem}.o"
        # Use GNU as for assembly (supports .code32/.code64 directives)
        # Run from pkg_dir so .incbin relative paths work
        as_cmd = ["as", "--64", "-o", str(obj_path), str(asm_file)]
        result = subprocess.run(as_cmd, capture_output=True, text=True, cwd=str(pkg_dir))
        if result.returncode != 0:
            print(f"  ✗ as failed for {asm_file.name}: {result.stderr}", file=sys.stderr)
            return None
        objects.append(obj_path)
    return objects


def freestanding_runtime_object(bin_config: BinaryConfig) -> Optional[Path]:
    """The _start shim a link_runtime [[bin]] links first: it calls main()
    and then sys_exit(). None once a failure has been reported."""
    # Determine the runtime variant based on main_args and target_os
    runtime_variant = {3: "ritz_start_envp", 2: "ritz_start"}.get(
        bin_config.main_args, "ritz_start_noargs")
    # Choose OS-specific runtime
    if bin_config.target_os == "harland":
        runtime_suffix = ".harland.x86_64.o"
    else:
        runtime_suffix = ".x86_64.o"
    runtime_name = f"{runtime_variant}{runtime_suffix}"
    runtime_path = RITZ0_DIR.parent / "runtime" / runtime_name

    if not ensure_runtime_object(runtime_path):
        # A freestanding/UEFI target can legitimately have no shim,
        # but link_runtime was explicitly requested — so this is fatal.
        print(f"  ✗ Could not provide runtime object: {runtime_path}", file=sys.stderr)
        return None
    print(f"  📦 Linking with runtime: {runtime_name}")
    return runtime_path


def link_uefi(name: str, bin_path: Path, object_files: list[Path]) -> bool:
    """Link a PE/COFF EFI application with lld-link. False once reported."""
    # Use find_llvm_tool so versioned installs (lld-link-19, ...) are
    # found — a bare which("lld-link") misses every distro package that
    # only ships the versioned name.
    lld_link = find_llvm_tool("lld-link")
    if not shutil.which(lld_link):
        # No lld-link: fail loudly rather than attempt the impossible.
        #
        # The objects we just produced are PE/COFF (compiled with
        # --target=x86_64-unknown-windows-gnu). The old fallback tried
        # to link them as an ELF shared object with `lld`, which
        # find_llvm_tool() silently degrades to GNU `ld` when LLVM's
        # linker is absent. GNU ld cannot link COFF input, so it died
        # on the Win64 ABI's mandatory SEH unwind data with:
        #
        #   dangerous relocation: R_AMD64_IMAGEBASE with __ImageBase
        #   undefined
        #
        # That is not a fixable link — it is a category error, and the
        # error text points at relocations rather than the real cause
        # (a missing tool). `__ImageBase` is supplied by lld-link
        # itself, so there is nothing to define our way out of.
        print(
            f"  ✗ Cannot link UEFI target '{name}': lld-link not found.\n"
            f"    UEFI binaries are PE/COFF and require LLVM's COFF "
            f"linker; GNU ld cannot link COFF objects.\n"
            f"    Install it with:  sudo apt install lld",
            file=sys.stderr,
        )
        record_setup_miss(name, "lld-link")
        return False

    # Direct PE/COFF linking with lld-link: a proper PE32+ with the
    # optional header UEFI expects.
    print(f"  📦 Linking PE/COFF with lld-link...")
    link_cmd = [lld_link, "/subsystem:efi_application", "/entry:efi_main",
                f"/out:{bin_path}", *[str(obj) for obj in object_files]]
    result = subprocess.run(link_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ lld-link failed: {result.stderr}", file=sys.stderr)
        return False
    return True


def link_freestanding_elf(bin_config: BinaryConfig, bin_path: Path,
                          object_files: list[Path]) -> bool:
    """Link a freestanding ELF with ld.lld (GNU ld if absent). False once
    reported."""
    link_cmd = [find_llvm_tool("lld")]
    # For PIE executables, add -pie flag and --no-dynamic-linker
    # (freestanding PIE doesn't need a dynamic linker)
    if bin_config.pic:
        link_cmd.extend(["--pie", "--no-dynamic-linker"])
    linker_script = bin_config.linker_script
    if linker_script and linker_script.exists():
        link_cmd.extend(["-T", str(linker_script)])
    link_cmd.extend(["-o", str(bin_path)])
    link_cmd.extend([str(obj) for obj in object_files])

    result = subprocess.run(link_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ ld.lld linking failed: {result.stderr}", file=sys.stderr)
        return False
    return True


def compile_freestanding_binary(
    bin_config: BinaryConfig,
    out_dir: Path,
    pkg_dir: Path,
    keep_artifacts: bool = False,
    use_cache: bool = True,
    profile: dict = None,
    dependencies: dict[str, DependencySpec] = None,
    source_roots: list[str] = None,
    compiler: str = "ritz0",
) -> Path:
    """Compile a freestanding binary (kernel, bootloader, etc.).

    Its modules go through the same stages as compile_binary's
    (discover_modules, compile_modules), for `freestanding_target(bin_config)`
    (AGAST #1835). Unlike compile_binary(), this:
    - Links the Ritz runtime only if the bin asks for it (link_runtime)
    - Compiles objects for the bin's own target triple and flags
    - Assembles .s files
    - Links with ld.lld using a custom linker script, or lld-link for UEFI

    Args:
        bin_config: BinaryConfig with freestanding options
        out_dir: Output directory
        pkg_dir: Package directory
        keep_artifacts: Keep .ll, .o files
        use_cache: Use build cache
        profile: Build profile (unused: the bin's own flags decide)
        dependencies: RFC #109 dependencies
        source_roots: List of source directories to search for imports
        compiler: "ritz0", "ritz1" or "ritz1_selfhosted". Never silently
            substituted (AGAST #1473): a ritz1-family build that ritz1 cannot
            honour fails with the reason instead of falling back to ritz0.
    """
    name = bin_config.name
    is_uefi = "uefi" in (bin_config.target or "x86_64-none-elf").lower()
    # Output binary path (ELF for kernels, EFI for UEFI)
    bin_path = out_dir / (f"{name.upper()}.EFI" if is_uefi else f"{name}.elf")

    if keep_artifacts:
        artifact_dir = out_dir / "obj"
        artifact_dir.mkdir(exist_ok=True)
    else:
        artifact_dir = Path(tempfile.mkdtemp())

    try:
        # Freestanding builds name their source roots absolutely and do not
        # pass --project-root to the compiler; kept as it was before the
        # stages were shared (AGAST #1835), so the IR is unchanged.
        abs_source_roots = [str(pkg_dir / sr) for sr in source_roots] if source_roots else None

        # Step 1: Discover all Ritz source files via imports
        all_sources = discover_modules(bin_config.src_path, project_root=pkg_dir,
                                       dependencies=dependencies,
                                       source_roots=abs_source_roots)
        if all_sources is None:
            return None

        # AGAST #1896: objects come from, and go to, the shared store, as
        # compile_binary's do, keyed by this target's object flags.
        cache = get_build_cache(compiler)
        cache.set_import_context(
            project_root=pkg_dir,
            dependencies={n: (s.path, s.sources) for n, s in (dependencies or {}).items()},
            source_roots=source_roots,
        )

        # Step 2: Compile each Ritz source to LLVM IR, then to an object,
        # through the same stages as a hosted binary (AGAST #1835).
        print(f"  Compiling {len(all_sources)} Ritz source file(s)...")
        object_files = compile_modules(
            all_sources, artifact_dir, cache=cache, store=cas.ArtifactStore(),
            use_cache=use_cache, compiler=compiler, dependencies=dependencies,
            source_roots=abs_source_roots, pkg_dir=None,
            target=freestanding_target(bin_config))
        if object_files is None:
            return None

        # Step 3: Assemble .s files
        if bin_config.asm_files:
            asm_objects = assemble_objects(bin_config.asm_files, pkg_dir, artifact_dir)
            if asm_objects is None:
                return None
            object_files.extend(asm_objects)

        # Step 3.5: Add runtime object file if requested (first in the link)
        if bin_config.link_runtime and not is_uefi:
            runtime_path = freestanding_runtime_object(bin_config)
            if runtime_path is None:
                return None
            object_files.insert(0, runtime_path)

        # Step 4: Link
        print(f"  ⚡ Linking {len(object_files)} object files...")
        if is_uefi:
            linked = link_uefi(name, bin_path, object_files)
        else:
            linked = link_freestanding_elf(bin_config, bin_path, object_files)
        return bin_path if linked else None

    finally:
        # Clean up temp directory if not keeping artifacts
        if not keep_artifacts and artifact_dir.exists():
            shutil.rmtree(artifact_dir, ignore_errors=True)


@dataclass
class PackageBuildResult:
    """Outcome of building one package: what built, what did NOT, what was skipped.

    build_package() used to return only the list of binaries that succeeded, so
    `if not built:` was the only available predicate — and that is true only
    when *zero* binaries built. A package declaring two binaries where the
    primary one failed to link still returned a non-empty list and therefore
    reported success (AGAST #1314: `build.py build ../zeus` exited 0 with
    `zeus` itself absent from build/debug/).

    The predicate is not "did anything build" but "did every target we were
    asked to build produce an artifact". Skips are permitted, but only when
    explicitly named in `skipped` — never inferred from a short list.
    """
    built: list[Path]
    failed: list[str]
    skipped: list[SkippedBinary]
    # The subset of `failed` that failed only because a toolchain binary is
    # missing from this machine (AGAST #2141). Still failures -- `ok` is
    # False -- but the environment's fault, not the code's.
    setup_failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True only when no declared target failed."""
        return not self.failed

    @property
    def setup_only(self) -> bool:
        """Failed, and every failure was a missing tool (exit EXIT_SETUP)."""
        return bool(self.failed) and set(self.failed) <= set(self.setup_failed)

    def __bool__(self) -> bool:
        # Deliberate: truth-testing the result means "did the package build?",
        # so the historical `if not built:` shape stays correct rather than
        # silently reverting to "did anything build?".
        return self.ok

    def summary(self) -> str:
        """One-line human description of the failure, for callers to print."""
        parts = [f"{len(self.failed)} of {len(self.built) + len(self.failed)} "
                 f"targets failed: {', '.join(self.failed)}"]
        if self.skipped:
            parts.append("skipped: " + ", ".join(
                f"{s.name} ({s.reason})" for s in self.skipped))
        return "; ".join(parts)


def build_package(pkg_dir: Path, config: dict, keep_artifacts: bool = False, use_cache: bool = True, profile_name: str = None, compiler: str = "ritz0") -> PackageBuildResult:
    """Build all binaries and libraries in a package.

    Args:
        pkg_dir: Package directory (where ritz.toml is)
        config: Parsed ritz.toml config
        keep_artifacts: Keep intermediate .ll files for debugging
        use_cache: Use build cache to skip unchanged files
        profile_name: Build profile ("debug", "release", or None for default)
        compiler:    "ritz0" (Python bootstrap, default) or "ritz1" (self-hosted).
                     When "ritz1", each source is compiled via the ritz1 binary
                     instead of ritz0.py. ritz1 has a minimal CLI so we skip the
                     --deps/--sources/--project-root plumbing and rely on -I
                     plus the standard RITZ_PATH for import resolution.
    """
    pkg_name = config["package"]["name"]
    profile = get_build_profile(config, profile_name)
    out_dir = get_output_dir(pkg_dir, profile)

    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)

    # Parse dependencies (RFC #109 Phase 2)
    dependencies = parse_dependencies(config, pkg_dir)

    # Get source roots for import resolution
    # Check top-level, [package], and [build] sections
    source_roots = config.get("sources")
    if source_roots is None:
        source_roots = config.get("package", {}).get("sources")
    if source_roots is None:
        source_roots = config.get("build", {}).get("sources")
    # Convert single string to list
    if isinstance(source_roots, str):
        source_roots = [source_roots]

    if dependencies:
        print(f"📦 Building {pkg_name} ({profile['name']}) with {len(dependencies)} dependencies...")
    else:
        print(f"📦 Building {pkg_name} ({profile['name']})...")

    # What the compiler resolves imports against: the declared dependencies
    # plus the package's own name (AGAST #1538). Kept separate from
    # `dependencies` so the banner above still counts only declared deps.
    namespaces = package_import_namespaces(config, pkg_dir)

    plan = plan_binaries(pkg_dir, config)
    binaries = plan.buildable
    built = []
    # A target that could not even be resolved is a failure, not an absence.
    failed = [u.name for u in plan.unresolved]
    setup_failed = []       # subset of `failed`: missing tool only (#2141)
    _SETUP_MISSES.clear()   # a miss belongs to the package that recorded it

    def note_failure(target: str) -> None:
        print(f"\n  ✗ Failed to build {target}")
        failed.append(target)
        tool = _SETUP_MISSES.pop(target, None)
        if tool:
            print(f"  ⚠ SETUP ERROR: {target} needs {tool}, which this "
                  f"machine lacks -- not verified here, not a regression")
            setup_failed.append(target)

    def display_path(path: Path) -> Path:
        # Not everything is under ROOT (e.g. running from a subdirectory).
        for base in (ROOT, Path.cwd()):
            try:
                return path.relative_to(base)
            except ValueError:
                pass
        return path

    for unresolved in plan.unresolved:
        print(f"  ✗ {unresolved.name}: {unresolved.reason}", file=sys.stderr)

    for skipped in plan.skipped:
        print(f"  ⏭ {skipped.name} skipped: {skipped.reason}")

    for bin_config in binaries:
        # Show source files being compiled
        try:
            src_rel = bin_config.src_path.relative_to(pkg_dir)
        except ValueError:
            src_rel = bin_config.src_path

        # Did this target print its 🔨 line? Freestanding does so up front;
        # the hosted branch below defers it (AGAST #1382).
        announced = True
        if bin_config.freestanding:
            # Freestanding build (kernel, bootloader)
            asm_count = len(bin_config.asm_files) if bin_config.asm_files else 0
            target_info = bin_config.target or "freestanding"
            print(f"  🔨 {bin_config.name} <- {src_rel} ({target_info}, {asm_count} asm files)", end="")

            bin_path = compile_freestanding_binary(
                bin_config=bin_config,
                out_dir=out_dir,
                pkg_dir=pkg_dir,
                keep_artifacts=keep_artifacts,
                use_cache=use_cache,
                profile=profile,
                dependencies=namespaces,
                source_roots=source_roots,
                compiler=compiler,
            )
        else:
            # Standard hosted build.
            #
            # AGAST #1382 (the #1360 rule): build.py never prints 🔨/✓ for
            # work it did not do. Either it rebuilt, and says 🔨 ... ✓, or the
            # binary was proven up to date, and it says exactly that. So the
            # 🔨 line is deferred until compile_binary commits to a rebuild.
            if bin_config.additional_sources:
                all_srcs = [src_rel] + [s.relative_to(pkg_dir) for s in bin_config.additional_sources]
                src_display = ", ".join(str(s) for s in all_srcs)
                hammer = f"  🔨 {bin_config.name} <- [{src_display}]"
            else:
                hammer = f"  🔨 {bin_config.name} <- {src_rel}"
            announced = False

            def announce_rebuild(hammer=hammer):
                nonlocal announced
                announced = True
                print(hammer, end="")

            bin_path = compile_binary(
                bin_config.name, bin_config.src_path, out_dir,
                additional_sources=bin_config.additional_sources,
                keep_artifacts=keep_artifacts,
                use_cache=use_cache,
                profile=profile,
                dependencies=namespaces,
                pkg_dir=pkg_dir,
                source_roots=source_roots,
                compiler=compiler,
                on_rebuild=announce_rebuild,
            )
            if not bin_path and not announced:
                # Failed before committing to a rebuild (e.g. import
                # resolution): still name the target the error belongs to.
                print(hammer, end="")
        if bin_path:
            rel_path = display_path(bin_path)
            if announced:
                print(f"\n  ✓ {rel_path}")
            else:
                print(f"  = {bin_config.name} up to date: {rel_path}")
            built.append(bin_path)

            # RFC convention: maintain a symlink at pkg_dir/<name> pointing at
            # the profile binary. Integration tests in test/*.ritz commonly
            # fork/exec `./<name>` (e.g. tier1/01_hello/test uses c"./hello"),
            # which means the binary has to live at pkg_dir/<name> when tests
            # run with cwd=pkg_dir. Symlink avoids copying (bin_path may be
            # large) and always reflects the most recent build profile.
            convenience_link = pkg_dir / bin_config.name
            try:
                if convenience_link.is_symlink() or convenience_link.exists():
                    # Replace stale target (old committed binary OR previous
                    # build's symlink pointing at a different profile)
                    convenience_link.unlink()
                # Use relative target so the symlink survives directory moves
                try:
                    rel_target = bin_path.relative_to(pkg_dir)
                except ValueError:
                    rel_target = bin_path
                convenience_link.symlink_to(rel_target)
            except OSError as e:
                # Non-fatal: a broken convenience symlink just means tests that
                # exec `./<name>` will fail — the build itself is still good.
                print(f"  ⚠ Could not create convenience symlink {convenience_link}: {e}",
                      file=sys.stderr)
        else:
            note_failure(bin_config.name)

    for lib in plan.libraries:
        # `lib<name>`: a package's library and binary usually share a name.
        target = f"lib{lib.name}"
        count = len(lib.modules)
        hammer = f"  🔨 {target} <- {count} module{'' if count == 1 else 's'}"
        announced = False

        def announce_library(hammer=hammer):
            nonlocal announced
            announced = True
            print(hammer, end="")

        archive = compile_library(
            lib, out_dir,
            keep_artifacts=keep_artifacts,
            use_cache=use_cache,
            dependencies=namespaces,
            pkg_dir=pkg_dir,
            source_roots=source_roots,
            compiler=compiler,
            on_rebuild=announce_library,
        )
        if not archive:
            note_failure(target)
        elif announced:
            print(f"\n  ✓ {display_path(archive)}")
            built.append(archive)
        else:
            print(f"  = {target} up to date: {display_path(archive)}")
            built.append(archive)

    return PackageBuildResult(built=built, failed=failed, skipped=plan.skipped,
                              setup_failed=setup_failed)


def ritz_path_for_tests(caller_path: str) -> str:
    """RITZ_PATH for test children: this tree's ROOT first, then the
    caller's entries, deduplicated by resolved path.

    ROOT goes FIRST because import resolution is first-match-wins and a
    leaked RITZ_PATH from a parent shell may point at a *different
    worktree* — its ritzlib must not shadow this tree's when build.py is
    invoked directly (`python3 build.py test ...`, `make test`). This
    matches the ritz1 compile-step ordering ("Put ROOT first (ritzlib
    priority)") elsewhere in this file. ROOT is resolved so symlinked or
    relative spellings of the same directory don't survive as duplicates.
    """
    root_str = str(ROOT.resolve())
    caller_entries = [p for p in caller_path.split(":") if p]
    kept = [p for p in caller_entries if str(Path(p).resolve()) != root_str]
    return ":".join([root_str] + kept)


_HARNESS_SUMMARY = re.compile(r"(\d+) passed, (\d+) failed(?:, (\d+) errored)?")


def classify_test_file(returncode: int, stdout: str) -> tuple[str, int, int]:
    """Classify one `ritz0 --test <file>` run as (status, passed, failed).

    status is one of:
      pass   exited 0, printed a harness summary, at least one test ran, none failed
      fail   the harness ran and at least one test failed
      error  non-zero exit, no harness summary, or "K errored": a file
             that did not compile or link (AGAST #3795), or a crash
      empty  exited 0 and ran ZERO tests

    `empty` is a failure, not a pass (AGAST #1345). `ritz0 --test` prints
    "0 passed, 0 failed" and exits 0 for a file with no [[test]] function,
    and this used to be reported as "✓ file — 0 passed". A test file that
    cannot fail cannot be told apart from one that does not exist.
    """
    passed = failed = errored = 0
    seen = False
    for line in stdout.splitlines():
        m = _HARNESS_SUMMARY.search(line)
        if m:  # last matching line wins
            passed, failed = int(m.group(1)), int(m.group(2))
            errored = int(m.group(3) or 0)
            seen = True
    # A file that did not build ran no test: not an assertion failure.
    if errored > 0:
        return "error", passed, failed
    # Checked BEFORE the exit code: `ritz0 --test` exits 1 when a test fails.
    # The old inline parser tested `returncode != 0` first, so every
    # assertion failure was reported as a compile failure and the Σ line's
    # "failed" count could only ever be 0.
    if failed > 0:
        return "fail", passed, failed
    if returncode != 0 or not seen:
        return "error", passed, failed
    if passed == 0:
        return "empty", passed, failed
    return "pass", passed, failed


def format_test_summary(n_files: int, tests_passed: int, tests_failed: int,
                        n_fail: int, n_error: int, n_empty: int,
                        n_timeout: int) -> str:
    """The Σ line for a package's .ritz test files.

    The headline counts FILES that did not pass. It used to read

        Σ 255 passed, 0 failed, 3 compile-failed, 0 timed-out

    and "0 failed" beside three compile failures reads as green to anyone
    scanning a log (AGAST #1345). A file that failed to compile has not
    passed. Zero counts are left out, so nothing prints "0 failed".
    """
    not_passing = n_fail + n_error + n_empty + n_timeout
    if not_passing == 0:
        return f"  Σ ✓ {n_files} of {n_files} files passed ({tests_passed} tests)"
    parts = []
    if n_fail:
        parts.append(f"{n_fail} with failing tests ({tests_failed} failed)")
    if n_error:
        parts.append(f"{n_error} compile-failed")
    if n_empty:
        parts.append(f"{n_empty} with no [[test]] functions")
    if n_timeout:
        parts.append(f"{n_timeout} timed-out")
    ok = n_files - not_passing
    return (f"  Σ ✗ {not_passing} of {n_files} files FAILED: {', '.join(parts)}"
            f" | {ok} file(s) passed, {tests_passed} tests passed")


def discover_test_files(pkg_dir: Path, config: dict) -> list[Path]:
    """The package's .ritz test files, sorted: test/*.ritz, plus the root's
    test_*.ritz for a `test_only` package.

    The single owner of test-file discovery. `run_tests` (serial) and the
    `--unit-plan` entry point that `rz test --all -j N` schedules from both
    call this, so the parallel sweep cannot cover a different file set from
    the serial one (AGAST #1809).
    """
    ritz_tests = []
    test_dir = pkg_dir / "test"
    if test_dir.exists():
        ritz_tests.extend(test_dir.glob("*.ritz"))
    if config.get("build", {}).get("test_only", False):
        ritz_tests.extend(pkg_dir.glob("test_*.ritz"))
    ritz_tests.extend(_declared_test_source_files(pkg_dir, config))
    return sorted(set(ritz_tests))  # Dedupe and sort


def _declared_test_source_files(pkg_dir: Path, config: dict) -> list[Path]:
    """Files under `[test] sources` dirs that define a `[[test]]` fn.

    For packages that keep [[test]] fns inside their modules rather than in
    test/ (angelo: `[test] sources = ["src"]`). `ritz0 --test` runs only the
    given file's own [[test]] fns, so each such module is its own test file.
    Dirs are searched recursively; a module with no `[[test]]` line is not
    taken, since it would report "ran 0 tests" and fail. Until AGAST #3279
    build.py read no key for this and angelo's tests ran under no gate.

    Only the `[test]` table counts. `[[test]]` in ritz.toml (goliath, spire)
    parses as a list of entry-point test binaries whose `sources` feed their
    builds, not this discovery; reading it as the table crashed `rz test`
    for both (AGAST #3290).
    """
    test_cfg = config.get("test")
    if not isinstance(test_cfg, dict):
        return []
    found = []
    for rel in test_cfg.get("sources", []):
        d = pkg_dir / rel
        if not d.is_dir():
            continue
        for f in d.rglob("*.ritz"):
            text = f.read_text(encoding="utf-8", errors="replace")
            if any(line.strip() == "[[test]]" for line in text.splitlines()):
                found.append(f)
    return found


def test_env_for_files() -> dict:
    """Environment for `ritz0 --test` children.

    Preserve any caller-provided RITZ_PATH — the workspace `rz` CLI builds a
    per-project dependency path list and passes it down; this used to
    REPLACE it with just the ritz root, silently breaking `lib.*` imports
    from path-dependencies in tests (AGAST #1324).
    """
    test_env = os.environ.copy()
    test_env["RITZ_PATH"] = ritz_path_for_tests(test_env.get("RITZ_PATH", ""))
    return test_env


def per_file_timeout() -> int:
    """Per-file timeout budget. 180s handles even slow elliptic-curve bigint
    tests on a debug build; can be tuned via RITZ_TEST_TIMEOUT."""
    return int(os.environ.get("RITZ_TEST_TIMEOUT", "180"))


@dataclass
class _TestRun:
    """What one `ritz0 --test <file>` printed, and its exit code."""
    returncode: int
    stdout: str
    stderr: str


def _ritz0_test_subprocess(tfile: Path, pkg_dir: Path, test_env: dict,
                           timeout: int, compiler: str) -> Optional[_TestRun]:
    """`ritz0 --test <tfile>` as a child process; None if it timed out."""
    cmd = [sys.executable, str(RITZ0), "--test", str(tfile)]
    if compiler != "ritz0":
        cmd += ["--compiler", compiler]
    try:
        r = subprocess.run(cmd, cwd=pkg_dir, env=test_env, capture_output=True,
                           text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    return _TestRun(r.returncode, r.stdout, r.stderr)


_TEST_RUNNER = None


def _test_runner():
    """ritz0/test_runner.py, imported once (RITZ0_DIR is on sys.path)."""
    global _TEST_RUNNER
    if _TEST_RUNNER is None:
        import importlib
        tr = importlib.import_module("test_runner")
        # It loads build.py for the store key and object flags; in this
        # process that is us, already imported. (A module exec'd by path
        # without registering itself is absent: test_runner loads its own.)
        if tr._BUILD_MODULE is None and sys.modules.get(__name__) is not None:
            tr._BUILD_MODULE = sys.modules[__name__]
        _TEST_RUNNER = tr
    return _TEST_RUNNER


def _can_run_in_process() -> bool:
    """The in-process timeout is a SIGALRM, which only the main thread gets."""
    return threading.current_thread() is threading.main_thread()


class _TestFileTimeout(BaseException):
    """Raised by SIGALRM. A BaseException, so run_files' per-file `except
    Exception` cannot turn the timeout into an ordinary failure."""


def _ritz0_test_in_process(tfile: Path, pkg_dir: Path, test_env: dict,
                           timeout: int, compiler: str) -> Optional[_TestRun]:
    """What `ritz0 --test <tfile>` would print, without starting it.

    AGAST #1915: the subprocess cost a second interpreter, ritz0.py's imports
    and test_runner's on every file unit, ~0.7 s per file before any work.
    test_runner.run_files is the code `ritz0 --test` runs, so the report (and
    classify_test_file's verdict) is the same. The child ran in pkg_dir with
    test_env (integration tests `fork/exec ./binary`); so does this, and both
    are put back afterwards. None if `timeout` expired: SIGALRM unwinds the
    run, and subprocess.run kills whatever child was running.
    """
    import contextlib
    import io

    tr = _test_runner()
    tfile = tfile.resolve()  # relative to our cwd, not pkg_dir
    out, err = io.StringIO(), io.StringIO()
    old_cwd, old_env = os.getcwd(), os.environ.copy()

    def on_alarm(_signum, _frame):
        raise _TestFileTimeout()

    old_handler = signal.signal(signal.SIGALRM, on_alarm)
    try:
        try:
            signal.setitimer(signal.ITIMER_REAL, timeout)
            os.environ.clear()
            os.environ.update(test_env)
            os.chdir(pkg_dir)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = tr.run_files([str(tfile)], compiler=compiler)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    except _TestFileTimeout:
        return None
    finally:
        signal.signal(signal.SIGALRM, old_handler)
        os.chdir(old_cwd)
        os.environ.clear()
        os.environ.update(old_env)
    return _TestRun(rc, out.getvalue(), err.getvalue())


def run_test_file(tfile: Path, pkg_dir: Path, test_env: dict,
                  timeout: int, compiler: str = "ritz0") -> dict:
    """Run one `ritz0 --test <tfile>` and print its verdict line(s).

    In-process on the main thread (AGAST #1915), as a `ritz0.py --test` child
    otherwise; both run test_runner.run_files and print the same report.

    `compiler` builds the test binary (`--compiler`, AGAST #1908): with a
    ritz1-family compiler, ritz0.py only drives the harness; every object in
    the binary, ritzunit's included, is compiled by `compiler`.

    Returns {"status", "passed", "failed"}, status being one of
    classify_test_file's statuses or "timeout". Shared by the serial loop
    in run_tests and by the `--unit-file` entry point, so a file's verdict
    and its printed lines are identical in both modes.

    Execution CWD matters for integration tests that `fork/exec ./binary`
    (see tier1/01_hello's test_hello_output). We run from pkg_dir so those
    relative paths work; imports still resolve via RITZ_PATH (env-based,
    not CWD-based — see ritz0/import_resolver.py).
    """
    run = _ritz0_test_in_process if _can_run_in_process() else _ritz0_test_subprocess
    result = run(Path(tfile), Path(pkg_dir), test_env, timeout, compiler)
    if result is None:
        print(f"    ⏱  {tfile.name} — TIMEOUT after {timeout}s")
        return {"status": "timeout", "passed": 0, "failed": 0}

    relay_compiler_warnings(result.stderr)
    status, file_passed, file_failed = classify_test_file(
        result.returncode, result.stdout)
    outcome = {"status": status, "passed": file_passed, "failed": file_failed}

    if status == "empty":
        print(f"    ✗ {tfile.name} — ran 0 tests: no [[test]] functions "
              f"(a test file that cannot fail is not a test)")
    elif status == "error":
        # Compile / link / runtime failure before harness summary
        err_blob = (result.stderr or "") + (result.stdout or "")
        # Try to surface the most actionable line
        err_first = ""
        for line in err_blob.splitlines():
            # Case-insensitive "error" so compiler diagnostics like
            # "Error in <file>: ..." match. The old tag list required
            # a literal "error:", missed them, and fell through to the
            # last line of output — which for a compile failure is the
            # content-free "  - <file>: error" harness summary line
            # (AGAST #1324).
            low = line.lower()
            if any(tag in low for tag in (
                "cannot select", "fatal error", "error", "valueerror:",
                "unknown function", "illegal instruction", "segmentation fault",
            )):
                err_first = line.strip()
                break
        if not err_first:
            err_first = err_blob.strip().splitlines()[-1] if err_blob.strip() else "(no output)"
        print(f"    ✗ {tfile.name} — {err_first[:200]}")
    elif status == "fail":
        # Compiled and ran but some assertions failed: surface the failing
        # harness messages.
        print(f"    ✗ {tfile.name} — {file_passed} passed, {file_failed} failed")
        for line in result.stdout.splitlines():
            if "FAIL" in line or "assertion" in line.lower():
                print(f"        {line}")
    else:
        print(f"    ✓ {tfile.name} — {file_passed} passed")
    return outcome


def summarize_file_outcomes(outcomes: list[dict]) -> str:
    """The Σ line for a list of run_test_file outcomes."""
    by = lambda s: sum(1 for o in outcomes if o["status"] == s)  # noqa: E731
    # Assertion counts only from files whose harness summary was trusted,
    # exactly as the serial loop always counted them.
    counted = [o for o in outcomes if o["status"] in ("pass", "fail")]
    return format_test_summary(
        n_files=len(outcomes),
        tests_passed=sum(o["passed"] for o in counted),
        tests_failed=sum(o["failed"] for o in counted),
        n_fail=by("fail"),
        n_error=by("error"),
        n_empty=by("empty"),
        n_timeout=by("timeout"),
    )


def run_test_sh(pkg_dir: Path) -> bool:
    """Run pkg_dir/test.sh (caller checks it exists); print its verdict."""
    print(f"  🧪 Running test.sh...")
    result = subprocess.run(
        ["bash", str(pkg_dir / "test.sh")],
        cwd=pkg_dir,
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"    ✓ test.sh passed")
        return True
    print(f"  ✗ test.sh failed:")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return False


def run_tests(pkg_dir: Path, config: dict, compiler: str = "ritz0") -> bool:
    """Run tests for a package with `compiler`.

    Every test binary is built by `compiler`: the test file in test mode,
    its dependencies and ritzunit (AGAST #1908). Before that, ritz1 had no
    test mode and its files were reported as NOT run (#1500): a ritz1 run
    must never fall back to ritz0.
    """
    all_passed = True
    tests_found = False

    ritz_tests = discover_test_files(pkg_dir, config)

    if ritz_tests:
        tests_found = True
        print(f"  🧪 Running {len(ritz_tests)} .ritz test file(s)...")
        # ritz0 --test compiles a test-harness binary and then EXECUTES it.
        # We run files ONE AT A TIME rather than passing all files to a single
        # ritz0 invocation: a single shared 5-minute deadline used to be enough
        # to kill the whole suite when any one file (e.g. ed25519, p256) was
        # slow to optimize, AND a single compile-time failure (e.g. an unknown
        # intrinsic) would terminate the batch before later files could run.
        # Per-file invocations cost a bit more on Python startup but give
        # accurate aggregate results and let one bad file fail in isolation.
        # (`rz test --all -j N` runs these same per-file units concurrently
        # across the workspace via --unit-file; AGAST #1809.)
        test_env = test_env_for_files()
        timeout = per_file_timeout()
        outcomes = [run_test_file(t, pkg_dir, test_env, timeout, compiler)
                    for t in ritz_tests]
        if any(o["status"] != "pass" for o in outcomes):
            all_passed = False
        print(summarize_file_outcomes(outcomes))

    # Run test.sh if it exists
    if (pkg_dir / "test.sh").exists():
        tests_found = True
        if not run_test_sh(pkg_dir):
            all_passed = False

    if not tests_found:
        print(f"  ⚠ No tests found, skipping")

    return all_passed


def cmd_list(args):
    """List all packages under current directory."""
    packages = find_all_packages()
    if not packages:
        print("No packages found (no ritz.toml files)")
        return 0

    print(f"Found {len(packages)} packages:\n")
    cwd = Path.cwd()
    for pkg_dir, config in packages:
        pkg_name = config["package"]["name"]
        plan = plan_binaries(pkg_dir, config)
        targets = [b.name for b in plan.buildable] + [f"lib{l.name}" for l in plan.libraries]
        is_test_only = config.get("build", {}).get("test_only", False)

        try:
            rel_path = pkg_dir.relative_to(cwd)
        except ValueError:
            rel_path = pkg_dir

        if is_test_only:
            print(f"  {rel_path}/  →  {pkg_name} (test-only)")
        elif targets:
            print(f"  {rel_path}/  →  {pkg_name} ({', '.join(targets)})")
        else:
            print(f"  {rel_path}/  →  {pkg_name}")


def cmd_build(args):
    """Build packages."""
    keep_artifacts = getattr(args, 'debug', False)
    use_cache = not getattr(args, 'no_cache', False)
    profile_name = "release" if getattr(args, 'release', False) else None
    compiler = getattr(args, 'compiler', 'ritz0')

    if args.all:
        # Build all packages under current directory
        targets = find_all_packages()
        if not targets:
            print("No packages found (no ritz.toml files)", file=sys.stderr)
            return 1
    elif args.name:
        # Try to find package by path or name
        result = find_package_by_name_or_path(args.name)
        if result:
            targets = [result]
        else:
            print(f"Package '{args.name}' not found", file=sys.stderr)
            return 1
    else:
        # No name specified - try current directory
        result = find_package_at(Path.cwd())
        if result:
            targets = [result]
        else:
            print("No ritz.toml found in current directory", file=sys.stderr)
            print("Usage: ritz build [path] or ritz build --all", file=sys.stderr)
            return 1

    success = True
    setup_only = True   # every failure so far was a missing tool (#2141)
    for pkg_dir, config in targets:
        # A test-only package (`[build] test_only = true`) deliberately declares
        # no [[bin]], so get_binaries() returns [] and build_package() returns an
        # empty list. That is success, not failure.
        #
        # cmd_test() already special-cases these; cmd_build() did not, so the
        # empty result silently flipped success to False and `build --all`
        # exited 1 having printed no error whatsoever — the package name was the
        # last thing on stdout. Keep the two commands in agreement.
        if config.get("build", {}).get("test_only", False):
            print(f"📦 {config['package']['name']} (test-only, nothing to build)")
            continue

        result = build_package(pkg_dir, config, keep_artifacts=keep_artifacts, use_cache=use_cache, profile_name=profile_name, compiler=compiler)
        # `result.ok` is "every declared binary produced an artifact", NOT
        # "at least one did" — see PackageBuildResult (AGAST #1314).
        if not result.ok:
            print(f"  ✗ Failed to build {config['package']['name']}: {result.summary()}",
                  file=sys.stderr)
            success = False
            setup_only = setup_only and result.setup_only

    if keep_artifacts:
        print(f"\n📁 Debug artifacts kept in build/")

    if success:
        return 0
    # A missing tool is neither a pass nor the code's fault: its own code, so
    # `rz build --all` (and the room gate) can say which (AGAST #2141).
    return EXIT_SETUP if setup_only else 1


# --- `rz test --all -j N` units (AGAST #1809) ------------------------------
#
# The workspace `rz` schedules a package's test run as independent units on
# one bounded worker pool, so files from different packages (and different
# files of one package) run concurrently:
#
#   --unit-plan PATH     build the package (exactly what `test` builds) and
#                        write the plan: which test files to run, whether
#                        test.sh exists. Exit 0 iff the build succeeded and
#                        the files can be run with this compiler.
#   --unit-file F        run ONE test file (no build); write its outcome to
#                        --unit-result. Exit 0 iff it passed.
#   --unit-test-sh       run test.sh only (no build).
#
# Each unit prints exactly the lines the serial `test` prints for that step
# (same helpers), and `rz` prints the buffered units back in serial order with
# the same Σ line (summarize_file_outcomes), so the verdict and the log read
# the same in both modes. Discovery stays here (discover_test_files); `rz`
# never globs test files itself.

def _test_unit_mode(args) -> Optional[str]:
    modes = [m for m, v in (("plan", getattr(args, "unit_plan", None)),
                            ("file", getattr(args, "unit_file", None)),
                            ("test-sh", getattr(args, "unit_test_sh", False)))
             if v]
    if len(modes) > 1:
        sys.exit("build.py test: --unit-plan, --unit-file and --unit-test-sh "
                 "are mutually exclusive")
    if modes == ["file"] and not getattr(args, "unit_result", None):
        sys.exit("build.py test: --unit-file needs --unit-result PATH")
    return modes[0] if modes else None


def unit_plan(pkg_dir: Path, config: dict, plan_path: Path, *,
              keep_artifacts: bool, use_cache: bool,
              profile_name: Optional[str], compiler: str) -> int:
    """Build step of a package's test run; writes the plan JSON.

    Mirrors cmd_test's per-package build branch and run_tests' preamble:
    a failed build runs nothing (built=false), and test.sh still runs.
    """
    import json
    pkg_name = config["package"]["name"]
    built = True
    if config.get("build", {}).get("test_only", False):
        print(f"📦 {pkg_name} (test-only)")
    else:
        result = build_package(pkg_dir, config, keep_artifacts=keep_artifacts,
                               use_cache=use_cache, profile_name=profile_name,
                               compiler=compiler)
        if not result.ok:
            print(f"  ✗ Failed to build {pkg_name}: {result.summary()}",
                  file=sys.stderr)
            built = False

    files: list[Path] = []
    if built:
        files = discover_test_files(pkg_dir, config)
    plan = {
        "built": built,
        "files": [str(f) for f in files],
        "test_sh": built and (pkg_dir / "test.sh").exists(),
    }
    plan_path.write_text(json.dumps(plan))
    return 0 if built else 1


def unit_file(pkg_dir: Path, tfile: Path, result_path: Path,
              compiler: str = "ritz0") -> int:
    """Run one test file; write its run_test_file outcome as JSON."""
    import json
    outcome = run_test_file(tfile, pkg_dir, test_env_for_files(),
                            per_file_timeout(), compiler)
    result_path.write_text(json.dumps(outcome))
    return 0 if outcome["status"] == "pass" else 1


def cmd_test(args):
    """Build and test packages."""
    keep_artifacts = getattr(args, 'debug', False)
    use_cache = not getattr(args, 'no_cache', False)
    profile_name = "release" if getattr(args, 'release', False) else None
    compiler = getattr(args, 'compiler', 'ritz0')

    if args.all:
        # Test all packages under current directory
        targets = find_all_packages()
        if not targets:
            print("No packages found (no ritz.toml files)", file=sys.stderr)
            return 1
    elif args.name:
        # Try to find package by path or name
        result = find_package_by_name_or_path(args.name)
        if result:
            targets = [result]
        else:
            print(f"Package '{args.name}' not found", file=sys.stderr)
            return 1
    else:
        # No name specified - try current directory
        result = find_package_at(Path.cwd())
        if result:
            targets = [result]
        else:
            print("No ritz.toml found in current directory", file=sys.stderr)
            print("Usage: ritz test [path] or ritz test --all", file=sys.stderr)
            return 1

    unit = _test_unit_mode(args)
    if unit:
        if len(targets) != 1 or args.all:
            print(f"--unit-{unit} takes exactly one package, not --all",
                  file=sys.stderr)
            return 2
        pkg_dir, config = targets[0]
        if unit == "plan":
            return unit_plan(pkg_dir, config, Path(args.unit_plan),
                             keep_artifacts=keep_artifacts, use_cache=use_cache,
                             profile_name=profile_name, compiler=compiler)
        if unit == "file":
            return unit_file(pkg_dir, Path(args.unit_file),
                             Path(args.unit_result), compiler)
        return 0 if run_test_sh(pkg_dir) else 1

    all_passed = True
    for pkg_dir, config in targets:
        # Check if this is a test-only package
        is_test_only = config.get("build", {}).get("test_only", False)

        if is_test_only:
            # For test-only packages, run tests directly without building a binary
            print(f"📦 {config['package']['name']} (test-only)")
            if not run_tests(pkg_dir, config, compiler):
                all_passed = False
        else:
            # Normal package: build then test
            result = build_package(pkg_dir, config, keep_artifacts=keep_artifacts, use_cache=use_cache, profile_name=profile_name, compiler=compiler)

            # A partial build is a build failure: running the test suite
            # against a package whose main binary does not exist reports on a
            # program that was never produced (AGAST #1314). The old predicate
            # here was `if built:` — truthy on a partial build.
            #
            # A package with nothing to build (only script [[bin]]s, all named
            # skips) has result.ok == True and goes straight to its tests, as
            # before.
            if not result.ok:
                print(f"  ✗ Failed to build {config['package']['name']}: {result.summary()}",
                      file=sys.stderr)
                all_passed = False
            elif not run_tests(pkg_dir, config, compiler):
                all_passed = False

    if keep_artifacts:
        print(f"\n📁 Debug artifacts kept in build/")

    if all_passed:
        print(f"\n✓ All tests passed!")
    else:
        print(f"\n✗ Some tests failed")

    return 0 if all_passed else 1


def cmd_ritz_tests(args):
    """Run ritz0's own .ritz test suite."""
    ritz0_dir = ROOT / "ritz0"
    test_dir = ritz0_dir / "test"

    if not test_dir.exists():
        print("No ritz0/test directory found", file=sys.stderr)
        return 1

    ritz_tests = sorted(test_dir.glob("test_level*.ritz"))
    if not ritz_tests:
        print("No test_level*.ritz tests found in ritz0/test/", file=sys.stderr)
        return 1

    print(f"🧪 Running ritz0 test suite ({len(ritz_tests)} levels)...")
    result = subprocess.run(
        [sys.executable, str(RITZ0), "--test-all", "-v"],
        cwd=ritz0_dir
    )
    return result.returncode


def cmd_run(args):
    """Compile and run a single .ritz file."""
    src_path = Path(args.file)
    if not src_path.exists():
        print(f"File not found: {src_path}", file=sys.stderr)
        return 1

    keep_artifacts = getattr(args, 'debug', False)
    name = src_path.stem

    # Use build/ directory for output
    out_dir = ROOT / "build"
    out_dir.mkdir(exist_ok=True)

    # AGAST #1382: announce 🔨 only if compile_binary actually rebuilds.
    announced = False

    def announce_rebuild():
        nonlocal announced
        announced = True
        print(f"🔨 Compiling {src_path}...")

    bin_path = compile_binary(name, src_path, out_dir, keep_artifacts=keep_artifacts,
                              on_rebuild=announce_rebuild)
    if not bin_path:
        return 1
    if not announced:
        print(f"= {bin_path.name} up to date")

    print(f"🚀 Running {bin_path.name}...", flush=True)
    print(flush=True)  # Blank line before output

    # Run the binary with any additional arguments
    result = subprocess.run([str(bin_path)] + args.args)
    return result.returncode


def cmd_clean(args):
    """Remove build artifacts.

    build_package writes every binary, `lib<name>.a` and manifest into
    `<pkg>/build/<profile>/` (get_output_dir), so removing those directories
    removes the build. Anything else under `<pkg>/build/` is left alone.
    """
    import shutil

    def shown(path: Path) -> Path:
        # RITZ_BUILD_CACHE_DIR (#2793) can put the cache outside ROOT.
        return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path

    for pkg_dir, config in find_packages():
        for profile_name in ("debug", "release"):
            out_dir = get_output_dir(pkg_dir, get_build_profile(config, profile_name))
            if out_dir.is_dir():
                shutil.rmtree(out_dir)
                print(f"  🗑 {shown(out_dir)}")

    # Clean pycache
    for pycache in ROOT.rglob("__pycache__"):
        shutil.rmtree(pycache)

    # Clean build cache
    cache = get_build_cache()
    if cache.cache_dir.exists():
        shutil.rmtree(cache.cache_dir)
        print(f"  🗑 {shown(cache.cache_dir)}")

    print("✓ Cleaned")


def cmd_cache_status(args):
    """Show cache status.

    The build cache holds the compiler fingerprint and persisted import scans;
    compiled modules live in the CAS (`python3 cas.py path`).
    """
    cache = get_build_cache()

    if not cache.cache_dir.exists():
        print("No cache exists")
        return 0

    print(f"Cache directory: {cache.cache_dir}")
    print(f"Import scans: {cache.import_scan_count()}")

    if args.verbose:
        print("\nScanned files:")
        for key in sorted(cache._load_imports_db()):
            path = key.rsplit("\0", 1)[-1]
            try:
                print(f"  {Path(path).relative_to(ROOT)}")
            except ValueError:
                print(f"  {path}")

    return 0


def cmd_cache_clear(args):
    """Clear the build cache."""
    cache = get_build_cache()
    cache.clear()
    print("Cache cleared")
    return 0


def main():
    parser = argparse.ArgumentParser(description="🎭 Ritz Build System")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all packages")

    # build
    build_parser = subparsers.add_parser("build", help="Build packages")
    build_parser.add_argument("name", nargs="?", help="Package path or directory (default: current directory)")
    build_parser.add_argument("--all", action="store_true", help="Build all packages under current directory")
    build_parser.add_argument("--release", action="store_true",
                              help="Build with release profile (optimizations enabled)")
    build_parser.add_argument("-g", "--debug", action="store_true",
                              help="Keep intermediate files (.ll, .o) in build/ for debugging")
    build_parser.add_argument("--no-cache", action="store_true",
                              help="Disable build cache (always rebuild)")
    build_parser.add_argument("--compiler", choices=["ritz0", "ritz1", "ritz1_selfhosted"], default="ritz0",
                              help="Which compiler to use (default: ritz0). ritz1 is the self-hosted "
                                   "compiler; ritz1_selfhosted is ritz1 compiled by itself.")

    # test
    test_parser = subparsers.add_parser("test", help="Build and test packages")
    test_parser.add_argument("name", nargs="?", help="Package path or directory (default: current directory)")
    test_parser.add_argument("--all", action="store_true", help="Test all packages under current directory")
    test_parser.add_argument("--release", action="store_true",
                             help="Build with release profile before testing")
    test_parser.add_argument("-g", "--debug", action="store_true",
                             help="Keep intermediate files (.ll, .o) in build/ for debugging")
    test_parser.add_argument("--no-cache", action="store_true",
                             help="Disable build cache (always rebuild)")
    test_parser.add_argument("--compiler", choices=["ritz0", "ritz1", "ritz1_selfhosted"], default="ritz0",
                             help="Which compiler to use (default: ritz0). ritz1 is the self-hosted "
                                  "compiler; ritz1_selfhosted is ritz1 compiled by itself.")
    # Unit entry points for the workspace `rz test --all -j N` worker pool
    # (AGAST #1809); see unit_plan / unit_file. Not meant for direct use.
    test_parser.add_argument("--unit-plan", metavar="PATH",
                             help=argparse.SUPPRESS)
    test_parser.add_argument("--unit-file", metavar="FILE",
                             help=argparse.SUPPRESS)
    test_parser.add_argument("--unit-result", metavar="PATH",
                             help=argparse.SUPPRESS)
    test_parser.add_argument("--unit-test-sh", action="store_true",
                             help=argparse.SUPPRESS)

    # run
    run_parser = subparsers.add_parser("run", help="Compile and run a single .ritz file")
    run_parser.add_argument("file", help="Ritz source file to run")
    run_parser.add_argument("args", nargs="*", help="Arguments to pass to the program")
    run_parser.add_argument("-g", "--debug", action="store_true",
                            help="Keep intermediate files in build/ for debugging")

    # clean
    subparsers.add_parser("clean", help="Remove build artifacts and cache")

    # ritz-tests
    subparsers.add_parser("ritz-tests", help="Run ritz0's .ritz test suite")

    # cache-status
    cache_status_parser = subparsers.add_parser("cache-status", help="Show build cache status")
    cache_status_parser.add_argument("-v", "--verbose", action="store_true",
                                      help="Show detailed cache information")

    # cache-clear
    subparsers.add_parser("cache-clear", help="Clear the build cache")

    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "build": cmd_build,
        "test": cmd_test,
        "run": cmd_run,
        "clean": cmd_clean,
        "ritz-tests": cmd_ritz_tests,
        "cache-status": cmd_cache_status,
        "cache-clear": cmd_cache_clear,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
