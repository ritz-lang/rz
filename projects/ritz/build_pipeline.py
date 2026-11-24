"""The build pipeline: compile a package's modules and link its targets.

Split out of build.py (AGAST #3632). Owns the per-module stages (discover,
emit, verify, `clang -c`, store), the hosted / freestanding / UEFI links,
the [[lib]] archive, binary provenance, and `build_package`, which runs a
package's whole plan. build.py re-exports all of it.
"""

import sys
import os
import hashlib
import json
import re
import subprocess
import shutil
import signal
import tempfile
import textwrap
import threading
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import bounded_run
from cache import BuildCache
import cas
from manifest import (BinaryConfig, LibraryConfig, SkippedBinary, StrayTestsDirError,
                      discover_test_files, get_build_profile,
                      plan_binaries, wants_convenience_link)
from resolve import DependencySpec, package_import_namespaces, package_sources, parse_dependencies


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
# The one `_start` (docs/V1_ABI_CLEANUP.md, AGAST #200): it calls
# main(argc, argv, envp) whatever shape `main` is written in.
RITZ_START = RUNTIME_DIR / f"ritz_start.{ARCH}.o"


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

    result = bounded_run.step(cmd + [str(ll_path)], capture_output=True, text=True)
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


def scratch_dir(cache: BuildCache) -> Path:
    """A fresh dir for one build's .ll/.o files, under `cache`'s directory.

    Not tempfile.mkdtemp(): /tmp is a tmpfs on the gate hosts, so every
    package build the ritz0 suite runs held its artifacts in RAM (AGAST
    #3906).  The cache dir is on disk, and a caller already moves it with
    RITZ_BUILD_CACHE_DIR (the suite: into the test's own dir).  The caller
    removes it, as it did the temp dir.
    """
    root = cache.cache_dir / "scratch"
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(dir=root))


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


# A top-level private fn, whose symbol carries its file (AGAST #1858), and a
# generic declaration, whose instance is emitted in another file's object and
# may call that fn by its symbol (#4356, #4608). Line-based and generous: a
# false match only costs a store hit.
_PRIVATE_FN_RE = re.compile(r"^(?:(?:async|const|unsafe)\s+)*fn\s+(?!main\b)\w", re.M)
_GENERIC_DECL_RE = re.compile(
    r"^\s*(?:pub\s+)?(?:fn\s+\w+\s*<|impl\s*<|struct\s+\w+\s*<|enum\s+\w+\s*<)", re.M)


def _path_bound_modules(src: Path, closure) -> List[str]:
    """Resolved paths of the modules among `src` and `closure` whose symbols
    an object built in another directory would spell differently.

    A private fn's symbol hashes its file's path relative to its checkout
    (ritz0 symbol_file_key, ritz1 fn_symbol; AGAST #4626), which
    cas.module_identity's repository-relative identity already pins. A file
    outside the repository (a test's tmp_path fixture, another checkout) has
    identity `ext/<name>` only, so two directories' copies shared a key while
    their objects named different symbols: a harness compiled in one linked
    against the other's object and failed with an undefined `helper__<hash>`.
    Such a module's path joins the key when it has a private fn that a
    generic's instance can reach from another object.
    """
    bound = []
    for p in {Path(p).resolve() for p in [src, *closure]}:
        if not cas.module_identity(p).startswith("ext/"):
            continue
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        if _PRIVATE_FN_RE.search(text) and _GENERIC_DECL_RE.search(text):
            bound.append(str(p))
    return sorted(bound)


def _cas_key(src: Path, closure, cache: BuildCache, compiler: str,
             flags: dict) -> Optional[str]:
    """cas.module_key for `src` built by `compiler`, its imports digested the
    way that compiler reads them. None if an import does not parse."""
    flags = dict(flags)
    bound = _path_bound_modules(src, closure)
    if bound:
        flags["symbol_paths"] = bound
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
        result = bounded_run.step(
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


def _crosses_foreign_symlink(logical: Path, root: Path) -> bool:
    """True if `logical` passes through a symlink that is not an ancestor of
    `root`, i.e. this tree reaches the package through a link another tree
    may share. A symlink above ROOT (a symlinked home or ~/dev) is common to
    the whole tree and splits nothing."""
    root_ancestors = {root, *root.parents}
    for p in (logical, *logical.parents):
        if p in root_ancestors:
            return False
        if p.is_symlink():
            return True
    return False


def get_output_dir(pkg_dir: Path, profile: dict, invoked_as: Path | None = None) -> Path:
    """Get output directory for a build profile.

    Per RFC #109 §3.1:
    - Debug builds → build/debug/
    - Release builds → build/release/

    AGAST #3818: `invoked_as` is the path the package was named by, before
    symlinks were resolved. Overlay roots and worktrees that reach one
    package dir through a symlink would otherwise all link into the one
    `<pkg>/build/<profile>/<bin>`, and a caller running it right after its
    build returned could run the OTHER tree's binary. Such a build writes to
    `ROOT/build/linked/<name>-<hash of the logical path>/<profile>/` instead,
    a dir no other tree writes even if ROOT/build is itself shared.
    """
    if invoked_as is not None:
        logical = Path(os.path.abspath(invoked_as))
        if not logical.is_dir():
            logical = logical.parent     # named by its ritz.toml
        root = Path(os.path.abspath(ROOT))
        if _crosses_foreign_symlink(logical, root):
            key = hashlib.sha256(str(logical).encode()).hexdigest()[:12]
            return root / "build" / "linked" / f"{pkg_dir.name}-{key}" / profile["name"]
    return pkg_dir / "build" / profile["name"]


def invoked_package_path(name_or_path: str | None) -> Path | None:
    """The logical (symlinks unresolved) path a package was named by, for
    get_output_dir. With no name the package is the cwd, whose getcwd() is
    already resolved: take $PWD when it names the same directory."""
    if name_or_path:
        path = Path(name_or_path)
        if not path.exists():
            path = Path.cwd() / name_or_path
        return Path(os.path.abspath(path)) if path.exists() else None
    pwd = os.environ.get("PWD")
    try:
        if pwd and os.path.samefile(pwd, os.getcwd()):
            return Path(pwd)
    except OSError:
        pass
    return None


def ritz1_compile_cmd(compiler: str, src: Path, ll_path: Path,
                      namespaces: dict | None = None) -> Optional[list]:
    """The ritz1-family command that compiles one source to LLVM IR.

    ritz1's CLI is minimal: <input> -o <output> [-I <ritz_path>]
    [--target-os <os>] [--target <triple>] [--dep <name>=<dir>]... It doesn't
    understand --no-runtime, --deps, --sources or --project-root; callers
    append --target-os and --target (Target.compiler_args) when they need them.
    Its default emitter is non-freestanding (no _start embedded), so the
    "--no-runtime" semantics come for free. Import resolution: ritz1 tries
    the `--dep` dirs first, then source_dir, then RITZ_PATH (see
    `ritz1_env`). `-I` points at the ritz ROOT so ritzlib/* imports resolve.

    `namespaces` (as for `ritz1_env`) become one `--dep <name>=<path>/<src>`
    per declared source root, in order: ritz0's `--deps` resolution, which
    reads a namespace's `sources`. Without it ritz1 probed only
    <ns>/{lib,src}, so zeus's `examples` root was invisible (AGAST #3825).

    Returns None (after saying why) if the binary is missing.
    """
    ritz1_bin, make_hint = RITZ1_FAMILY_BINS[compiler]
    if not ritz1_bin.exists():
        print(f"  ✗ {compiler} binary not found at {ritz1_bin}", file=sys.stderr)
        print(f"    Run: cd {ROOT} && {make_hint}", file=sys.stderr)
        return None
    cmd = [str(ritz1_bin), str(src), "-o", str(ll_path), "-I", str(ROOT)]
    for name, spec in (namespaces or {}).items():
        for source in spec.sources:
            cmd += ["--dep", f"{name}={Path(spec.path) / source}"]
    return cmd


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
    `stack_protector` passes the compiler's --stack-protector (AGAST #2590):
    the IR gets `sspstrong`, so the binary must define `__stack_chk_guard`
    and `__stack_chk_fail`.
    `no_red_zone` passes the compiler's --no-red-zone (AGAST #4308): the IR
    gets `noredzone`. The `-mno-red-zone` in `clang_flags` is a frontend
    flag that does nothing for .ll input, so without this harland's functions
    used the red zone.  A freestanding module's `triple` also goes to the
    compiler as --target (AGAST #3488; ritz1's too, #4607): it has to know a
    kernel from a hosted program to choose a trap's stop (ritz_platform_fatal,
    not exit).
    """
    freestanding: bool = False
    clang_flags: Tuple[str, ...] = ()
    target_os: str = ""
    stack_protector: bool = False
    no_red_zone: bool = False
    # The compiler's --target, so it knows the triple (AGAST #3488, #4607):
    # the kernel's traps and asserts must reach ritz_platform_fatal, not an
    # exit syscall.
    triple: str = ""

    @property
    def obj_flags(self) -> List[str]:
        """The flags compile_ll_to_obj runs clang with."""
        if not self.freestanding:
            return OBJ_CLANG_FLAGS
        return ["-c", *self.clang_flags]

    @property
    def key_flags(self) -> Optional[dict]:
        """cas_module_key's `object_flags`: None for the hosted defaults.
        Unchanged from AGAST #1896, so existing store entries stay valid;
        `stack_protector` and `no_red_zone` appear only when set, for the
        same reason. (`no_red_zone` must be in the key even though
        `-mno-red-zone` already is: entries stored before #4308 hold
        red-zone objects under the key that flag alone produces.)"""
        if not self.freestanding:
            return None
        flags = {"freestanding": True, "target_os": self.target_os,
                 "clang": list(self.clang_flags)}
        if self.stack_protector:
            flags["stack_protector"] = True
        if self.no_red_zone:
            flags["no_red_zone"] = True
        if self.triple:
            flags["target"] = self.triple
        return flags

    def compiler_args(self) -> List[str]:
        """Arguments the compiler (ritz0 or ritz1) takes for this target."""
        args = ["--target-os", self.target_os] if self.target_os else []
        if self.triple:
            args.extend(["--target", self.triple])
        if self.stack_protector:
            args.append("--stack-protector")
        if self.no_red_zone:
            args.append("--no-red-zone")
        return args


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
    result = _list_deps(src_path, project_root=project_root,
                        dependencies=dependencies, source_roots=source_roots)
    if result.returncode != 0:
        print(f"  ✗ import resolution failed: {result.stderr}", file=sys.stderr)
        _REACHED.incomplete = True
        return None
    modules = _listed_modules(result.stdout)
    _REACHED.modules.update(modules)
    return modules


def _list_deps(src_path: Path, *, project_root: Path,
               dependencies: dict[str, DependencySpec] = None,
               source_roots: list[str] = None,
               env: dict = None) -> subprocess.CompletedProcess:
    """ritz0/list_deps.py on `src_path`: its import closure, one per line."""
    cmd = [sys.executable, str(RITZ0_DIR / "list_deps.py"), str(src_path),
           "--project-root", str(project_root)]
    if dependencies:
        cmd.extend(["--deps", _deps_json(dependencies)])
    if source_roots:
        cmd.extend(["--sources", json.dumps(source_roots)])
    # The environment carries RITZ_PATH for import resolution.
    return bounded_run.step(cmd, capture_output=True, text=True,
                            env=env if env is not None else os.environ)


def _listed_modules(stdout: str) -> list[Path]:
    return [Path(f.strip()) for f in stdout.strip().split('\n') if f.strip()]


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


def test_env_for_files(use_cache: bool = True) -> dict:
    """Environment for `ritz0 --test` children.

    Preserve any caller-provided RITZ_PATH — the workspace `rz` CLI builds a
    per-project dependency path list and passes it down; this used to
    REPLACE it with just the ritz root, silently breaking `lib.*` imports
    from path-dependencies in tests (AGAST #1324).

    `use_cache=False` (`build.py test --no-cache`) sets test_runner's
    RITZ_NO_CAS too, so the test binaries' objects and harness are compiled,
    not served from the artifact store: the flag only reached the package
    build, and a stale store object kept failing a test link (AGAST #4626).
    """
    test_env = os.environ.copy()
    test_env["RITZ_PATH"] = ritz_path_for_tests(test_env.get("RITZ_PATH", ""))
    if not use_cache:
        test_env["RITZ_NO_CAS"] = "1"  # test_runner.NO_CAS_ENV
    return test_env


def test_reached_modules(pkg_dir: Path, config: dict, *,
                         dependencies: dict[str, DependencySpec] = None,
                         source_roots: list[str] = None) -> set[Path]:
    """Every module the package's test files import, transitively.

    `rz test` compiles these, so none is silently uncompiled: sage's lexer
    and parser are a library only its tests use (AGAST #2210). Resolved as
    `ritz0 --test` runs a test file: from pkg_dir, with the test RITZ_PATH.
    A test file whose imports do not resolve adds nothing: `rz test`
    already fails it with the reason.
    """
    try:
        tests = discover_test_files(pkg_dir, config)
    except StrayTestsDirError:
        return set()
    env = test_env_for_files()
    reached: set[Path] = set()
    for tfile in tests:
        result = _list_deps(tfile, project_root=pkg_dir, dependencies=dependencies,
                            source_roots=source_roots, env=env)
        if result.returncode == 0:
            reached.update(_listed_modules(result.stdout))
    return reached


class _ReachedModules:
    """Every module a target of the package being built reached (AGAST #2210).

    discover_modules adds each import closure and build_package the [[lib]]
    modules; build_package then reports the src/ modules missing from it.
    `incomplete` once any import resolution failed: the closure that failed
    is unknown, so nothing may then be called an orphan.
    """

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.modules: set[Path] = set()
        self.incomplete = False


_REACHED = _ReachedModules()


def _nested_package_dirs(src_dir: Path) -> list[Path]:
    """Dirs under `src_dir` holding their own ritz.toml: another package."""
    return [m.parent for m in src_dir.rglob("ritz.toml")]


def orphaned_modules(pkg_dir: Path, reached) -> list[Path]:
    """The pkg_dir/src/**/*.ritz modules no target compiled, sorted.

    `rz build` compiles only what an entry point imports, so a module
    nothing imports is never compiled and the build stays green: nexus's
    repos/, presenters/ and wiki_service could not even parse, unnoticed
    (AGAST #2210). Not orphans: `reached` (compared resolved), a module
    with a [[test]] fn (`rz test` compiles it, AGAST #3279) and a nested
    package's files.
    """
    src_dir = pkg_dir / "src"
    if not src_dir.is_dir():
        return []
    seen = {Path(p).resolve() for p in reached}
    nested = _nested_package_dirs(src_dir)
    orphans = []
    for f in sorted(src_dir.rglob("*.ritz")):
        if f.resolve() in seen or any(f.is_relative_to(d) for d in nested):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if any(line.strip() == "[[test]]" for line in text.splitlines()):
            continue
        orphans.append(f)
    return orphans


def module_compile_cmd(compiler: str, src: Path, ll_path: Path, target: Target, *,
                       dependencies: dict[str, DependencySpec] = None,
                       source_roots: list[str] = None,
                       pkg_dir: Path = None) -> Optional[list]:
    """The command that emits `src`'s IR to `ll_path` with no runtime.
    None when the ritz1-family compiler cannot be used (already reported)."""
    if compiler.startswith("ritz1"):
        # ritz1 emits no _start by default, which is what --no-runtime asks
        # of ritz0.
        cmd = ritz1_compile_cmd(compiler, src, ll_path, dependencies)
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
            result = bounded_run.step(compile_cmd, capture_output=True, text=True, env=env)
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

    result = bounded_run.step(link_cmd, capture_output=True, text=True)
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
            runtime=[ll for ll in (RITZ_START.with_suffix(".ll"),) if ll.exists()])
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
        artifact_dir = scratch_dir(cache)

    # One entry path: the same `_start` whatever shape `main` has.
    runtime_obj = RITZ_START

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

    artifact_dir = ROOT / "build" if keep_artifacts else scratch_dir(cache)
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
            result = bounded_run.step(
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
                  target_os=bin_config.target_os or "",
                  stack_protector=bool(bin_config.stack_protector),
                  no_red_zone=bool(bin_config.no_red_zone),
                  triple=target)


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
        result = bounded_run.step(as_cmd, capture_output=True, text=True, cwd=str(pkg_dir))
        if result.returncode != 0:
            print(f"  ✗ as failed for {asm_file.name}: {result.stderr}", file=sys.stderr)
            return None
        objects.append(obj_path)
    return objects


def freestanding_runtime_path(bin_config: BinaryConfig) -> Path:
    """Where the _start shim of a link_runtime [[bin]] lives (built or not)."""
    # One `_start` per OS; it calls main(argc, argv, envp) (AGAST #200).
    runtime_variant = "ritz_start"
    if bin_config.target_os == "harland":
        runtime_suffix = ".harland.x86_64.o"
    else:
        runtime_suffix = ".x86_64.o"
    return RITZ0_DIR.parent / "runtime" / f"{runtime_variant}{runtime_suffix}"


def freestanding_runtime_object(bin_config: BinaryConfig) -> Optional[Path]:
    """The _start shim a link_runtime [[bin]] links first: it calls main()
    and then sys_exit(). None once a failure has been reported."""
    runtime_path = freestanding_runtime_path(bin_config)
    runtime_name = runtime_path.name

    if not ensure_runtime_object(runtime_path):
        # A freestanding/UEFI target can legitimately have no shim,
        # but link_runtime was explicitly requested — so this is fatal.
        print(f"  ✗ Could not provide runtime object: {runtime_path}", file=sys.stderr)
        return None
    print(f"  📦 Linking with runtime: {runtime_name}")
    return runtime_path


def link_uefi(name: str, bin_path: Path, object_files: list[Path],
              entry_symbol: str) -> bool:
    """Link a PE/COFF EFI application with lld-link. False once reported.

    `entry_symbol` is the target's `[[bin]] entry` function half (AGAST
    #4434): UEFI is the one freestanding link that owns an entry symbol on
    its command line, so it comes from the manifest, not a hardcode. The
    PE entry is that function directly; a target with no `entry` uses the
    language entry, `main`.
    """
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
    link_cmd = [lld_link, "/subsystem:efi_application", f"/entry:{entry_symbol}",
                f"/out:{bin_path}", *[str(obj) for obj in object_files]]
    result = bounded_run.step(link_cmd, capture_output=True, text=True)
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

    result = bounded_run.step(link_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ ld.lld linking failed: {result.stderr}", file=sys.stderr)
        return False
    return True


def _file_record(path: Path) -> list:
    """[resolved path, sha256], the sha256 None if the file is absent."""
    return [str(path.resolve()), _sha256_file(path) if path.exists() else None]


def freestanding_provenance(bin_config: BinaryConfig, sources: list[Path], compiler: str,
                            compiler_hash: str, pkg_dir: Path) -> dict:
    """What a freestanding binary linked now would be built from (AGAST #3632).

    binary_provenance's record for its Ritz sources, plus what decides a
    freestanding binary's bytes and not a hosted one's: its target's object
    flags and link choices, each .s file with what it .incbin's (a missing
    one is skipped by the build, so its absence is recorded too), the linker
    script and the runtime shim. Raises OSError if a source is unreadable.
    """
    target = bin_config.target or "x86_64-none-elf"
    is_uefi = "uefi" in target.lower()
    runtime = []
    if bin_config.link_runtime and not is_uefi:
        runtime = [freestanding_runtime_path(bin_config).with_suffix(".ll")]
    record = binary_provenance(sources, compiler, compiler_hash, {},
                               runtime=[r for r in runtime if r.exists()])
    del record["profile"]   # unused: the bin's own flags decide
    asm = []
    for asm_file in bin_config.asm_files or []:
        incbins = []
        if asm_file.exists():
            incbins = [_file_record(pkg_dir / m.group(1))
                       for line in asm_file.read_text().split("\n")
                       if ".incbin" in line and (m := _INCBIN.search(line))]
        asm.append(_file_record(asm_file) + [incbins])
    script = bin_config.linker_script
    target_flags = {"objects": freestanding_target(bin_config).key_flags, "uefi": is_uefi,
                    "pic": bin_config.pic, "link_runtime": bin_config.link_runtime}
    if is_uefi:
        # The manifest's entry function half is the PE entry symbol (AGAST
        # #4434), so changing it must relink rather than reuse this binary.
        target_flags["entry"] = bin_config.entry_fn
    record.update(
        target=target_flags,
        asm=asm,
        linker_script=_file_record(script) if script else None,
    )
    return record


def _link_freestanding(bin_config: BinaryConfig, bin_path: Path, is_uefi: bool,
                       object_files: list[Path], provenance: Optional[dict]) -> bool:
    """Link to a private name, then publish it with its provenance (#1499)."""
    print(f"  ⚡ Linking {len(object_files)} object files...")
    linked = private_output_path(bin_path)
    try:
        if is_uefi:
            ok = link_uefi(bin_config.name, linked, object_files,
                           bin_config.entry_fn)
        else:
            ok = link_freestanding_elf(bin_config, linked, object_files)
        if ok:
            publish_binary(linked, bin_path, provenance)
        return ok
    finally:
        linked.unlink(missing_ok=True)


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
    on_rebuild=None,
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
        on_rebuild: as for compile_binary: called once real work starts, not
            when the binary is proven up to date (AGAST #3632).
    """
    name = bin_config.name
    is_uefi = "uefi" in (bin_config.target or "x86_64-none-elf").lower()
    # Output binary path (ELF for kernels, EFI for UEFI)
    bin_path = out_dir / (f"{name.upper()}.EFI" if is_uefi else f"{name}.elf")

    cache = get_build_cache(compiler)
    # As in compile_binary: a changed compiler drops the import scans, and
    # a binary the old one built is not up to date.
    compiler_changed = cache.invalidate_if_compiler_changed() if use_cache else False

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

    # AGAST #3632: the fast path compile_binary has had since #1382, on a
    # record of everything that decides a freestanding binary's bytes.
    try:
        provenance = freestanding_provenance(bin_config, all_sources, compiler,
                                             cache._get_current_compiler_hash(), pkg_dir)
    except OSError:
        provenance = None
    if (use_cache and provenance is not None and not compiler_changed
            and binary_is_up_to_date(bin_path, provenance)):
        return bin_path
    if on_rebuild is not None:
        on_rebuild()

    if keep_artifacts:
        artifact_dir = out_dir / "obj"
        artifact_dir.mkdir(exist_ok=True)
    else:
        artifact_dir = scratch_dir(cache)

    try:
        # AGAST #1896: objects come from, and go to, the shared store, as
        # compile_binary's do, keyed by this target's object flags.
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
        if not _link_freestanding(bin_config, bin_path, is_uefi, object_files, provenance):
            return None
        return bin_path

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
    # src/ modules no target compiled (AGAST #2210). Reported, never a
    # failure: `ok` ignores them.
    orphans: list[Path] = field(default_factory=list)

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


def _display_path(path: Path) -> Path:
    """`path` relative to ROOT or the cwd, for a ✓ line. Not everything is
    under ROOT (e.g. running from a subdirectory)."""
    for base in (ROOT, Path.cwd()):
        try:
            return path.relative_to(base)
        except ValueError:
            pass
    return path


@dataclass
class _PackageTally:
    """What build_package built and failed, as it goes; prints each target's
    verdict line."""
    built: list[Path] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    setup_failed: list[str] = field(default_factory=list)   # missing tool only (#2141)

    def done(self, target: str, path: Path, announced: bool) -> None:
        if announced:
            print(f"\n  ✓ {_display_path(path)}")
        else:
            print(f"  = {target} up to date: {_display_path(path)}")
        self.built.append(path)

    def fail(self, target: str) -> None:
        print(f"\n  ✗ Failed to build {target}")
        self.failed.append(target)
        tool = _SETUP_MISSES.pop(target, None)
        if tool:
            print(f"  ⚠ SETUP ERROR: {target} needs {tool}, which this "
                  f"machine lacks -- not verified here, not a regression")
            self.setup_failed.append(target)


def _build_bin_target(bin_config: BinaryConfig, pkg_dir: Path, out_dir: Path,
                      profile: dict, **common) -> tuple[Optional[Path], bool]:
    """Build one [[bin]] and print its 🔨 line. Returns (the binary or None,
    whether it was rebuilt: False when proven up to date). `common` is
    keep_artifacts, use_cache, dependencies, source_roots and compiler."""
    try:
        src_rel = bin_config.src_path.relative_to(pkg_dir)
    except ValueError:
        src_rel = bin_config.src_path

    # AGAST #1382 (the #1360 rule): build.py never prints 🔨/✓ for work it
    # did not do. Either it rebuilt, and says 🔨 ... ✓, or the binary was
    # proven up to date, and it says exactly that. So the 🔨 line is deferred
    # until the compile commits to a rebuild; for a freestanding binary
    # (kernel, bootloader) too, since AGAST #3632.
    if bin_config.freestanding:
        asm_count = len(bin_config.asm_files) if bin_config.asm_files else 0
        target_info = bin_config.target or "freestanding"
        hammer = f"  🔨 {bin_config.name} <- {src_rel} ({target_info}, {asm_count} asm files)"
    elif bin_config.additional_sources:
        all_srcs = [src_rel] + [s.relative_to(pkg_dir) for s in bin_config.additional_sources]
        src_display = ", ".join(str(s) for s in all_srcs)
        hammer = f"  🔨 {bin_config.name} <- [{src_display}]"
    else:
        hammer = f"  🔨 {bin_config.name} <- {src_rel}"
    announced = False

    def announce_rebuild():
        nonlocal announced
        announced = True
        print(hammer, end="")

    if bin_config.freestanding:
        bin_path = compile_freestanding_binary(
            bin_config=bin_config, out_dir=out_dir, pkg_dir=pkg_dir,
            profile=profile, on_rebuild=announce_rebuild, **common)
    else:
        bin_path = compile_binary(
            bin_config.name, bin_config.src_path, out_dir,
            additional_sources=bin_config.additional_sources, profile=profile,
            pkg_dir=pkg_dir, on_rebuild=announce_rebuild, **common)
    if not bin_path and not announced:
        # Failed before committing to a rebuild (e.g. import resolution):
        # still name the target the error belongs to.
        print(hammer, end="")
    return bin_path, announced


def _build_lib_target(lib: LibraryConfig, pkg_dir: Path, out_dir: Path,
                      **common) -> tuple[Optional[Path], bool]:
    """Build one [[lib]]; as _build_bin_target. Its 🔨 line names it
    `lib<name>`: a package's library and binary usually share a name."""
    count = len(lib.modules)
    hammer = f"  🔨 lib{lib.name} <- {count} module{'' if count == 1 else 's'}"
    announced = False

    def announce_library():
        nonlocal announced
        announced = True
        print(hammer, end="")

    archive = compile_library(lib, out_dir, pkg_dir=pkg_dir,
                              on_rebuild=announce_library, **common)
    return archive, announced


def link_convenience_binary(pkg_dir: Path, name: str, bin_path: Path) -> None:
    """Point `pkg_dir/<name>` at the profile binary.

    RFC convention: integration tests in test/*.ritz commonly fork/exec
    `./<name>` (e.g. tier1/01_hello/test uses c"./hello"), which means the
    binary has to live at pkg_dir/<name> when tests run with cwd=pkg_dir.
    Symlink avoids copying (bin_path may be large) and always reflects the
    most recent build profile.
    """
    convenience_link = pkg_dir / name
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


def build_package(pkg_dir: Path, config: dict, keep_artifacts: bool = False, use_cache: bool = True, profile_name: str = None, compiler: str = "ritz0", invoked_as: Path | None = None) -> PackageBuildResult:
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
        invoked_as:  The path the package was named by, symlinks unresolved
                     (invoked_package_path). Reached through another tree's
                     symlink, its outputs go to a per-root dir (#3818).
    """
    pkg_name = config["package"]["name"]
    profile = get_build_profile(config, profile_name)
    out_dir = get_output_dir(pkg_dir, profile, invoked_as=invoked_as)
    # Outputs outside the package dir: it is shared with another tree, so
    # nothing of this build may be written into it (#3818).
    out_of_pkg = not out_dir.is_relative_to(pkg_dir)

    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)

    # Parse dependencies (RFC #109 Phase 2)
    dependencies = parse_dependencies(config, pkg_dir)

    if dependencies:
        print(f"📦 Building {pkg_name} ({profile['name']}) with {len(dependencies)} dependencies...")
    else:
        print(f"📦 Building {pkg_name} ({profile['name']})...")
    if out_of_pkg:
        print(f"  ↪ reached through a symlink: outputs go to {out_dir}, "
              f"not {pkg_dir / 'build'} (#3818)")

    # What the compiler resolves imports against: the declared dependencies
    # plus the package's own name (AGAST #1538). Kept separate from
    # `dependencies` so the banner above still counts only declared deps.
    namespaces = package_import_namespaces(config, pkg_dir)
    common = dict(keep_artifacts=keep_artifacts, use_cache=use_cache,
                  dependencies=namespaces, source_roots=package_sources(config),
                  compiler=compiler)

    plan = plan_binaries(pkg_dir, config)
    # A target that could not even be resolved is a failure, not an absence.
    tally = _PackageTally(failed=[u.name for u in plan.unresolved])
    _SETUP_MISSES.clear()   # a miss belongs to the package that recorded it
    _REACHED.reset()        # as is a reached module (#2210)

    for unresolved in plan.unresolved:
        print(f"  ✗ {unresolved.name}: {unresolved.reason}", file=sys.stderr)

    for skipped in plan.skipped:
        print(f"  ⏭ {skipped.name} skipped: {skipped.reason}")

    for bin_config in plan.buildable:
        bin_path, announced = _build_bin_target(bin_config, pkg_dir, out_dir, profile, **common)
        if not bin_path:
            tally.fail(bin_config.name)
            continue
        tally.done(bin_config.name, bin_path, announced)
        # No `<pkg>/<name>` link when the outputs left the package dir: it
        # is shared, and a link there would hand this tree's binary to the
        # other's `./<name>` (#3818). None for a freestanding binary (#4131).
        if not out_of_pkg and wants_convenience_link(bin_config):
            link_convenience_binary(pkg_dir, bin_config.name, bin_path)

    for lib in plan.libraries:
        archive, announced = _build_lib_target(lib, pkg_dir, out_dir, **common)
        if archive:
            tally.done(f"lib{lib.name}", archive, announced)
        else:
            tally.fail(f"lib{lib.name}")
        _REACHED.modules.update(lib.modules)

    orphans = report_orphans(pkg_dir, attempted=bool(plan.buildable or plan.libraries),
                             display_path=_display_path,
                             test_reached=lambda: test_reached_modules(
                                 pkg_dir, config, dependencies=namespaces,
                                 source_roots=common["source_roots"]))
    return PackageBuildResult(built=tally.built, failed=tally.failed,
                              skipped=plan.skipped, setup_failed=tally.setup_failed,
                              orphans=orphans)


def report_orphans(pkg_dir: Path, *, attempted: bool, display_path,
                   test_reached=lambda: set()) -> list[Path]:
    """Print the src/ modules this build did not compile; return them.

    A report, not a failure (AGAST #2210): the gate's `rz build --all`
    stays a verdict on what is built, and an orphan is listed on every
    build until it is wired in or deleted. Silent when nothing was
    compiled (a test-only or script-only package). `test_reached()` gives
    the modules test files import; it is called only if a candidate is
    left, so a package with no orphan resolves no test file.
    """
    if not attempted:
        return []
    if _REACHED.incomplete:
        print("  ⚠ orphan check skipped: an import resolution failed, so "
              "which src/ modules are compiled is unknown")
        return []
    orphans = orphaned_modules(pkg_dir, _REACHED.modules)
    if orphans:
        orphans = orphaned_modules(pkg_dir, _REACHED.modules | test_reached())
    if orphans:
        n = len(orphans)
        print(f"  ⚠ {n} module{'s' if n != 1 else ''} under src/ "
              f"{'are' if n != 1 else 'is'} not compiled: no target or test "
              f"imports {'them' if n != 1 else 'it'} (AGAST #2210)")
        for f in orphans:
            print(f"    - {display_path(f)}")
    return orphans
