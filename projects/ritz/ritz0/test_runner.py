#!/usr/bin/env python3
"""
Ritz Test Runner: builds and runs one test binary per test file.

A test binary (LANGUAGE_SPEC.md §17.1, AGAST #1868) is

    the test file, compiled by `ritz0 --test-table`: its `[[test]]` table and
        a `_start` that calls `main`
  + ritzunit's `main` and runner, linked as ONE object whose only global
        symbol is `main` (so no runner name can collide with the program's)
  + the dependency objects of both.

It is compiled and linked once, run once with `--json`, and ritzunit runs each
test in its own forked child. This module turns the JSON report into
`run_test_file`'s (passed, failed, failures) for `ritz0 --test`.
"""

import sys
import argparse
import signal
import subprocess
import tempfile
import hashlib
import json
import os
import shutil
import threading
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from lexer import Lexer
from parser import Parser
from import_resolver import collect_all_source_files, DependencyMapping
import ritz_ast as rast

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11


def get_sources_from_config(config: dict) -> list:
    """Extract sources from a ritz.toml config.

    Handles the TOML quirk where sources may be nested under [package]
    or at top-level or under [build].
    """
    sources = config.get("sources")
    if sources is None:
        sources = config.get("package", {}).get("sources")
    if sources is None:
        sources = config.get("build", {}).get("sources")
    if sources is None:
        sources = ["src"]  # default
    if isinstance(sources, str):
        sources = [sources]
    return sources


def project_source_roots(project_root: Optional[Path]) -> List[str]:
    """Absolute, existing `sources` directories from project_root/ritz.toml.

    Passed to every ritz0 compile as `--sources` so a test file resolves
    imports the same way `rz build` resolves the package's own sources.
    Discovery (setup_test_environment) always used these roots; the dependency
    and harness compiles did not, so `import types.color` was found and then
    "Cannot find module" at compile time (AGAST #1686).
    """
    if project_root is None:
        return []
    toml_path = Path(project_root) / "ritz.toml"
    if not toml_path.exists():
        return []
    with open(toml_path, "rb") as f:
        config = tomllib.load(f)
    roots = [Path(project_root) / s for s in get_sources_from_config(config)]
    return [str(r) for r in roots if r.is_dir()]


# AGAST #1908: a test binary is built by one compiler, ritz0 by default. With
# a ritz1-family compiler every module is built by it: the test file
# (`ritz1 --test-table`), its dependencies and ritzunit's own sources.
def _ritz1_compile(compiler: str, src: str, out_ll: str, project_root: Optional[Path],
                   dependencies: Optional[Dict[str, DependencyMapping]],
                   *extra: str) -> Optional[str]:
    """Compile `src` to `out_ll` with a ritz1-family compiler; an error or None.

    The command and environment are build.py's (`ritz1_compile_cmd`,
    `ritz1_env`), so a module compiles exactly as `rz build --compiler ritz1`
    compiles it. ritz1 takes no --sources: the project's source roots go on
    RITZ_PATH instead, after build.py's entries, so `import types.color` from
    a test file resolves as it does under ritz0's `--sources`.
    """
    build = _build_module()
    cmd = build.ritz1_compile_cmd(compiler, Path(src), Path(out_ll))
    if cmd is None:
        return f"{compiler} binary not found"
    namespaces = {n: d for n, d in (dependencies or {}).items()
                  if isinstance(d.path, Path)}
    env = build.ritz1_env(namespaces)
    entries = env["RITZ_PATH"].split(os.pathsep)
    entries += [r for r in project_source_roots(project_root) if r not in entries]
    env["RITZ_PATH"] = os.pathsep.join(entries)
    result = subprocess.run(cmd + list(extra), capture_output=True, text=True, env=env)
    if result.returncode != 0:
        return f"{compiler} failed for {Path(src).name}: {result.stderr}{result.stdout}"
    return None


def _sources_args(project_root: Optional[Path]) -> List[str]:
    """`--sources <json>` for a ritz0 compile, or nothing if there are none."""
    import json
    roots = project_source_roots(project_root)
    return ["--sources", json.dumps(roots)] if roots else []


def parse_project_dependencies(project_root: Path) -> dict:
    """Parse dependencies from project's ritz.toml.

    Also adds a self-reference for the current project so tests can import
    from their own package using the package name (e.g., import cryptosec.u128).

    Returns a dict mapping dependency name to DependencyMapping.
    """
    toml_path = project_root / "ritz.toml"
    if not toml_path.exists():
        return {}

    with open(toml_path, "rb") as f:
        config = tomllib.load(f)

    dependencies = {}

    # Add self-reference for current project (Issue #48)
    # This allows tests to import from their own package using the package name
    pkg_name = config.get("package", {}).get("name")
    if pkg_name:
        pkg_sources = get_sources_from_config(config)
        # Check if sources actually exist, otherwise use root
        if pkg_sources == ["src"] and not (project_root / "src").is_dir():
            if (project_root / "lib").is_dir():
                pkg_sources = ["lib"]
            else:
                pkg_sources = ["."]
        dependencies[pkg_name] = DependencyMapping(
            name=pkg_name,
            path=project_root.resolve(),
            sources=pkg_sources
        )

    deps_config = config.get("dependencies", {})

    for name, spec in deps_config.items():
        if isinstance(spec, dict):
            dep_path = spec.get("path")
            if dep_path:
                dep_full_path = (project_root / dep_path).resolve()
                if dep_full_path.exists():
                    # Read the dependency's ritz.toml for sources
                    dep_toml = dep_full_path / "ritz.toml"
                    sources = ["src"]  # default
                    if dep_toml.exists():
                        with open(dep_toml, "rb") as f:
                            dep_config = tomllib.load(f)
                        sources = get_sources_from_config(dep_config)
                        # Check if sources exist, otherwise use root
                        if sources == ["src"] and not (dep_full_path / "src").is_dir():
                            sources = ["."]
                    else:
                        # No ritz.toml - check if src/ exists
                        if not (dep_full_path / "src").is_dir():
                            sources = ["."]
                    dependencies[name] = DependencyMapping(
                        name=name,
                        path=dep_full_path,
                        sources=sources
                    )
        elif isinstance(spec, str):
            dep_full_path = (project_root / spec).resolve()
            if dep_full_path.exists():
                dependencies[name] = DependencyMapping(
                    name=name,
                    path=dep_full_path,
                    sources=["src"]
                )

    return dependencies

# AGAST #1392. Scratch directories used to be created with
# `tempfile.mkdtemp(dir='.')`, i.e. inside the package under test, and populated
# with a `ritzlib` symlink so imports resolve. When the package under test was
# ritzlib itself, a leaked scratch dir left `ritzlib/tests/tmpXXXX/ritzlib`
# pointing at its own ancestor -- a cycle. pytest follows directory symlinks
# while collecting, so the ritz0 suite spent 739 s and collected zero tests.
#
# Putting scratch under the system temp dir makes that cycle unconstructible
# rather than merely unlikely: a directory outside the tree cannot be an
# ancestor of anything inside it. The (since deleted) batch runner already did
# this, so the two remaining sites were the anomaly, not the convention.
_SCRATCH_PREFIX = "ritz_test_"

# Registry of live scratch dirs, so a signal handler has something to clean.
# Without it the paths are locals in whichever frame happens to be running.
_SCRATCH_DIRS: set = set()
_SCRATCH_LOCK = threading.Lock()


def make_scratch_dir() -> str:
    """Create a scratch directory outside the tree under test, and register it."""
    path = tempfile.mkdtemp(prefix=_SCRATCH_PREFIX)
    with _SCRATCH_LOCK:
        _SCRATCH_DIRS.add(path)
    return path


def cleanup_scratch_dir(tmpdir: Optional[str]):
    """Remove a scratch directory and deregister it. Safe to call twice."""
    if not tmpdir:
        return
    with _SCRATCH_LOCK:
        _SCRATCH_DIRS.discard(tmpdir)
    if os.path.exists(tmpdir):
        cleanup_tmpdir_with_symlinks(tmpdir)


def _cleanup_all_scratch_dirs():
    with _SCRATCH_LOCK:
        live = list(_SCRATCH_DIRS)
    for path in live:
        cleanup_scratch_dir(path)


def install_signal_handlers():
    """Make SIGTERM/SIGINT unwind so the existing `finally` blocks run.

    A `finally` covers exceptions but not process death: CPython services the
    default SIGTERM by terminating without unwinding, which is why every
    `finally: cleanup...` in this file was silently bypassed whenever a run was
    killed or hit an outer `timeout`. Raising SystemExit from the handler turns
    the signal back into an ordinary unwind.

    Signal handlers can only be installed from the main thread; callers that are
    not on it get a no-op rather than an exception, since cleanup is a
    best-effort tidy-up and must never break a working run.
    """
    if threading.current_thread() is not threading.main_thread():
        return

    def _handler(signum, _frame):
        _cleanup_all_scratch_dirs()
        # 128+n is the conventional shell encoding for "killed by signal n";
        # preserving it keeps `timeout`'s 124/143 exit codes meaningful.
        raise SystemExit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError):
            # Some embedding contexts disallow this. Not fatal.
            pass


def cleanup_tmpdir_with_symlinks(tmpdir: str):
    """Clean up a temp directory that may contain symlinks.

    We must remove symlinks first (without following them) before
    removing the directory, otherwise shutil.rmtree might follow symlinks.
    """
    tmpdir_path = Path(tmpdir)
    # First pass: remove symlinks
    for item in tmpdir_path.iterdir():
        if item.is_symlink():
            item.unlink()
    # Second pass: remove everything else
    for item in tmpdir_path.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    # Finally remove the directory itself
    tmpdir_path.rmdir()


def find_test_functions(source_path: str) -> List[Tuple[str, rast.FnDef]]:
    """Find all @test functions in a source file."""
    source = Path(source_path).read_text()
    lexer = Lexer(source, source_path)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    module = parser.parse_module()

    tests = []
    for item in module.items:
        if isinstance(item, rast.FnDef) and item.has_attr('test'):
            tests.append((item.name, item))
    return tests


def strip_main_from_source(source: str) -> str:
    """Remove any existing main() function from source.

    This is a simple approach - find 'fn main()' and remove everything after it.
    This works because main() is typically at the end of test files.
    """
    # Find 'fn main(' or 'fn main()' - must be at start of line (possibly indented)
    lines = source.split('\n')
    result_lines = []
    in_main = False
    main_indent = 0

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('fn main(') or stripped.startswith('fn main ()'):
            in_main = True
            main_indent = len(line) - len(stripped)
            continue

        if in_main:
            # Check if we've exited main (new top-level definition)
            if stripped and not stripped.startswith('#'):
                current_indent = len(line) - len(stripped)
                if current_indent <= main_indent and (stripped.startswith('fn ') or
                                                       stripped.startswith('struct ') or
                                                       stripped.startswith('@') or
                                                       stripped.startswith('import ')):
                    in_main = False
                    result_lines.append(line)
            continue

        result_lines.append(line)

    return '\n'.join(result_lines)


def setup_test_environment(source_path: str, tmpdir: str) -> Tuple[Optional[Path], Optional[List[Path]], Optional[str], Optional[Dict[str, DependencyMapping]]]:
    """Set up test environment and discover dependencies.

    Returns:
        (project_root, dependency_files, error_message, dependencies)
        dependency_files excludes the test file itself
        dependencies is the parsed DependencyMapping dict from ritz.toml
    """
    # Copy helper files to temp directory
    test_dir = Path(source_path).parent
    for lib_file in test_dir.glob("test_import_*.ritz"):
        shutil.copy(lib_file, tmpdir)
    helpers_file = test_dir / "helpers.ritz"
    if helpers_file.exists():
        shutil.copy(helpers_file, tmpdir)

    # Find project root
    project_root = None
    search_dir = Path(source_path).parent.resolve()
    while search_dir != search_dir.parent:
        if (search_dir / "ritz.toml").exists():
            project_root = search_dir
            break
        search_dir = search_dir.parent

    # Parse dependencies from ritz.toml (Issue #48)
    dependencies = {}
    source_roots = None
    if project_root:
        dependencies = parse_project_dependencies(project_root)

        # Read source roots from project's ritz.toml
        source_roots = project_source_roots(project_root) or None

        # Add ritzlib to source roots (from ritz project or RITZ_PATH)
        ritz0_dir = Path(__file__).parent.resolve()
        ritzlib_path = ritz0_dir.parent / "ritzlib"
        # DEBUG: print(f"DEBUG: ritz0_dir={ritz0_dir}, ritzlib_path={ritzlib_path}, exists={ritzlib_path.exists()}", file=sys.stderr)
        if ritzlib_path.exists():
            if source_roots is None:
                source_roots = []
            # Add the parent of ritzlib so imports like 'ritzlib.sys' work
            source_roots.append(str(ritz0_dir.parent))

        # Symlink common source directories
        for src_dir in ["lib", "src"]:
            src_path = project_root / src_dir
            if src_path.exists():
                real_path = src_path.resolve()
                link_path = Path(tmpdir) / src_dir
                if not link_path.exists():
                    os.symlink(real_path, link_path)

        # Symlink ritzlib - try project root first, then RITZ_PATH
        ritzlib_link = Path(tmpdir) / "ritzlib"
        if not ritzlib_link.exists():
            ritzlib_path = project_root / "ritzlib"
            if ritzlib_path.exists():
                os.symlink(ritzlib_path.resolve(), ritzlib_link)
            else:
                # Try to find ritzlib from RITZ_PATH or parent directories
                ritz_path_env = os.environ.get("RITZ_PATH", "")
                for p in ritz_path_env.split(":"):
                    if p:
                        ritzlib_candidate = Path(p) / "ritzlib"
                        if ritzlib_candidate.exists():
                            os.symlink(ritzlib_candidate.resolve(), ritzlib_link)
                            break
                else:
                    # Fallback: look for ritzlib relative to this file (test_runner.py)
                    ritz0_dir = Path(__file__).parent
                    ritzlib_candidate = ritz0_dir.parent / "ritzlib"
                    if ritzlib_candidate.exists():
                        os.symlink(ritzlib_candidate.resolve(), ritzlib_link)

    # Discover dependencies using a dummy harness
    original_source = Path(source_path).read_text()
    source_no_main = strip_main_from_source(original_source)
    dummy_harness = source_no_main + "\nfn main() -> i32\n  0\n"
    dummy_path = os.path.join(tmpdir, "dummy_harness.ritz")
    Path(dummy_path).write_text(dummy_harness)

    try:
        source_files = collect_all_source_files(
            dummy_path,
            project_root=str(project_root) if project_root else None,
            dependencies=dependencies if dependencies else None,
            source_roots=source_roots
        )
        # Remove the dummy harness from the list
        source_files = [f for f in source_files if Path(f).name != "dummy_harness.ritz"]
        return project_root, source_files, None, dependencies
    except Exception as e:
        return None, None, f"Import resolution failed: {e}", None


# AGAST #1808: dependency objects come from the shared content-addressed
# store (projects/ritz/cas.py) that build.py writes, keyed exactly as build.py
# keys them. Before this every test file started from an empty in-memory
# cache and ran ritz0 once per module of its ritzlib closure: thousands of
# ritzlib compiles per `rz test --all`. Set RITZ_NO_CAS=1 to bypass it.
NO_CAS_ENV = "RITZ_NO_CAS"
_BUILD_MODULE = None


def _build_module():
    """build.py, imported once. It owns the store key and the object flags."""
    global _BUILD_MODULE
    if _BUILD_MODULE is None:
        import importlib.util
        pkg_dir = Path(__file__).resolve().parent.parent
        # Appended, not prepended: projects/ritz holds `packaging.py`, which
        # must not shadow the PyPI package. build.py itself is loaded by path,
        # because a bare `import build` finds whichever `build` comes first on
        # sys.path (the `ritz0/build/` output directory, PyPA's `build`).
        if str(pkg_dir) not in sys.path:
            sys.path.append(str(pkg_dir))
        spec = importlib.util.spec_from_file_location("ritz_build_py", pkg_dir / "build.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        _BUILD_MODULE = build
    return _BUILD_MODULE


def _cas_context(project_root, dependencies, compiler="ritz0"):
    """(build module, BuildCache, ArtifactStore) set up to resolve imports the
    way ritz0 is invoked below, or None if the store is disabled."""
    if os.environ.get(NO_CAS_ENV, "") not in ("", "0"):
        return None
    build = _build_module()
    cache = build.get_build_cache(compiler)
    cache.set_import_context(
        project_root=project_root,
        dependencies={n: (Path(d.path), list(d.sources)) for n, d in (dependencies or {}).items()},
        source_roots=project_source_roots(project_root),
    )
    return build, cache, build.cas.ArtifactStore()


def _ritz0_compile_dependency(ritz0_py: Path, src: str, ll_path: str,
                              project_root: Optional[Path],
                              dependencies: Optional[Dict[str, DependencyMapping]]
                              ) -> Optional[str]:
    """`ritz0 <src> --no-runtime` to `ll_path`; an error message or None."""
    import json
    compile_cmd = [sys.executable, str(ritz0_py), src, "-o", ll_path, "--no-runtime"]

    # Pass dependencies to ritz0 if provided (Issue #48)
    if dependencies:
        deps_json = {
            name: {"path": str(spec.path), "sources": spec.sources}
            for name, spec in dependencies.items()
        }
        compile_cmd.extend(["--deps", json.dumps(deps_json)])

    # Pass project root if provided
    if project_root:
        compile_cmd.extend(["--project-root", str(project_root)])
    compile_cmd.extend(_sources_args(project_root))

    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return f"ritz0 failed for {Path(src).name}: {result.stderr}"
    return None


def compile_dependencies(
    source_files: List[Path],
    tmpdir: str,
    ll_cache: dict,
    dependencies: Dict[str, DependencyMapping] = None,
    project_root: Path = None,
    compiler: str = "ritz0",
) -> Tuple[List[str], Optional[str]]:
    """Compile dependencies to LLVM IR with `compiler`, using cache when possible.

    Args:
        source_files: List of source files to compile
        tmpdir: Temp directory for .ll files
        ll_cache: Dict mapping source path -> compiled .ll path (shared across tests)
        dependencies: ritz.toml dependency mappings for import resolution
        project_root: Project root directory

    Returns:
        (ll_files, error_message)
    """
    import json
    ritz0_dir = Path(__file__).parent
    ritz0_py = ritz0_dir / "ritz0.py"
    ll_files = []
    ctx = _cas_context(project_root, dependencies, compiler) if source_files else None

    for src in source_files:
        src_key = str(Path(src).resolve())

        # Check cache first
        if src_key in ll_cache:
            ll_files.append(ll_cache[src_key])
            continue

        path_hash = hashlib.md5(src_key.encode()).hexdigest()[:8]
        src_name = f"{Path(src).stem}_{path_hash}"
        ll_path = os.path.join(tmpdir, f"{src_name}.ll")
        obj_path = os.path.join(tmpdir, f"{src_name}.o")

        cas_key = None
        if ctx is not None:
            build, cache, store = ctx
            cas_key = build.cas_module_key(Path(src_key), cache, compiler)

        def emit_ll(src=src, ll_path=ll_path) -> Optional[str]:
            """`compiler` --no-runtime of `src` into ll_path; an error, or None."""
            if compiler != "ritz0":
                return _ritz1_compile(compiler, str(src), ll_path, project_root, dependencies)
            return _ritz0_compile_dependency(ritz0_py, str(src), ll_path, project_root,
                                             dependencies)

        if cas_key is None:
            error = emit_ll()
            if error:
                return None, error
        else:
            def build_fn(emit_ll=emit_ll, ll_path=ll_path, obj_path=obj_path):
                # Same pipeline as build.py: compile, verify (if asked), clang -c.
                error = (emit_ll()
                         or build.verify_ir(Path(ll_path), Path(src_key))
                         or build.compile_ll_to_obj(Path(ll_path), Path(obj_path), Path(src_key)))
                if error:
                    raise build.cas.BuildFailed(error)
                return {"ll": Path(ll_path), "o": Path(obj_path)}
            # AGAST #1911: single-flight. Parallel test_runner processes that
            # miss on one key together compile it once; the rest wait and hit.
            ident = build.cas.module_identity(Path(src_key))
            try:
                stored, built = store.get_or_build(
                    cas_key, "o", build_fn, identity=ident,
                    meta={"module": ident, "compiler": compiler})
            except build.cas.BuildFailed as e:
                return None, str(e)
            if not built:
                shutil.copyfile(stored, obj_path)
            ll_path = obj_path

        ll_cache[src_key] = ll_path
        ll_files.append(ll_path)

    return ll_files, None


def _compile_harness(
    harness_path: str,
    harness_ll: str,
    project_root: Optional[Path],
    dependencies: Optional[Dict[str, DependencyMapping]],
    compiler: str = "ritz0",
) -> Optional[str]:
    """Compile a test file in test mode (`--test-table`) to LLVM IR.

    Compiled *with* the runtime: its `_start` calls ritzunit's `main`. Returns an
    error message, or None on success.
    """
    if compiler != "ritz0":
        return _ritz1_compile(compiler, harness_path, harness_ll, project_root,
                              dependencies, "--test-table")
    import json
    ritz0_py = Path(__file__).parent / "ritz0.py"
    compile_cmd = [sys.executable, str(ritz0_py), harness_path, "-o", harness_ll, "--test-table"]

    # Pass dependencies to ritz0 for harness compilation (Issue #48)
    if dependencies:
        deps_json = {
            name: {"path": str(spec.path), "sources": spec.sources}
            for name, spec in dependencies.items()
        }
        compile_cmd.extend(["--deps", json.dumps(deps_json)])

    # Pass project root for import resolution
    if project_root:
        compile_cmd.extend(["--project-root", str(project_root)])
    compile_cmd.extend(_sources_args(project_root))

    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return f"ritz0 failed for harness: {result.stderr}"
    return None


def _cas_enabled() -> bool:
    return os.environ.get(NO_CAS_ENV, "") in ("", "0")


def _harness_ll(source_path: str, harness_path: str, harness_ll: str,
                project_root: Optional[Path],
                dependencies: Optional[Dict[str, DependencyMapping]],
                closure: List[Path], compiler: str = "ritz0") -> Optional[str]:
    """Write the test file's `--test-table` IR to `harness_ll`; an error or None.

    AGAST #1915: from the artifact store when it has it, keyed on the harness
    source and its closure's interfaces (build.cas_harness_key). Before this
    every file of every warm `rz test --all` recompiled IR it had produced
    before: ~0.75 s x 180 files.
    """
    def compile_it() -> Optional[str]:
        return _compile_harness(harness_path, harness_ll, project_root, dependencies, compiler)

    if not _cas_enabled():
        return compile_it()
    build = _build_module()
    key = build.cas_harness_key(Path(harness_path), closure, compiler)
    if key is None:
        return compile_it()

    def build_fn():
        error = compile_it()
        if error:
            raise build.cas.BuildFailed(error)
        return {"ll": Path(harness_ll)}

    ident = build.cas.module_identity(Path(source_path)) + "#test-table"
    try:
        stored, built = build.cas.ArtifactStore().get_or_build(
            key, "ll", build_fn, identity=ident,
            meta={"module": ident, "compiler": compiler})
    except build.cas.BuildFailed as e:
        return str(e)
    if not built:
        shutil.copyfile(stored, harness_ll)
    return None


def _link(objects: List[str], exe_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Link objects / .ll files into an executable. Returns (exe_path, error)."""
    # -march=native enables host CPU features (AES-NI, AVX2, etc.).  -msha is
    # added unconditionally because cryptosec's sha256.ritz defines a
    # sha256_transform_ni function whose body emits SHA-NI intrinsics
    # (sha256rnds2/msg1/msg2).  Even when the public API never calls it (it
    # currently doesn't), LLVM's instruction selector still has to lower the
    # function body and aborts with "Cannot select intrinsic" without +sha.
    # On a host without SHA-NI silicon the binary will SIGILL only if the
    # function is actually called — pure-soft callers are safe.  This mirrors
    # the flag set used by build.py's link path.
    clang_cmd = ["clang"] + objects + ["-o", exe_path, "-nostdlib", "-no-pie", "-g", "-march=native", "-msha"]
    result = subprocess.run(clang_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, f"clang failed: {result.stderr}"
    return exe_path, None


# ---------------------------------------------------------------------------
# ritzunit: the `main` of every test binary (AGAST #1868)
# ---------------------------------------------------------------------------

RITZUNIT_ROOT = Path(__file__).resolve().parent.parent.parent / "ritzunit"
RITZUNIT_MAIN = RITZUNIT_ROOT / "src" / "bin_main.ritz"

# Per-test timeout handed to ritzunit (-t). The Python harness this replaced
# allowed each test 10 s.
TEST_TIMEOUT_MS = 10000


def runner_args() -> List[str]:
    """ritzunit's flags: the JSON report is what passes or fails the file."""
    return ["--json", "--no-color", "-t", str(TEST_TIMEOUT_MS)]


def _ritzunit_import_context():
    """(dependencies, source_roots) that ritzunit's own sources resolve under."""
    deps = parse_project_dependencies(RITZUNIT_ROOT)
    roots = project_source_roots(RITZUNIT_ROOT) + [str(Path(__file__).resolve().parent.parent)]
    return deps, roots


def _ritzunit_sources() -> List[str]:
    """ritzunit's source closure, as collect_all_source_files orders it.

    AGAST #1920: every file unit is its own process and resolved the same
    closure again (~900 Path.resolve calls, ~0.07 s); it is kept in the
    build.py closure memo, reused while every file has the same content.
    Raises what resolution raises.
    """
    deps, roots = _ritzunit_import_context()
    build = _build_module() if _cas_enabled() else None
    memo = None
    if build is not None:
        memo = {"kind": "ritzunit_sources", "main": str(RITZUNIT_MAIN),
                "root": str(RITZUNIT_ROOT), "roots": roots,
                "deps": sorted((n, str(d.path), list(d.sources)) for n, d in deps.items()),
                "ritz_path": os.environ.get("RITZ_PATH", "")}
        hit = build.closure_memo_get(memo)
        if hit is not None:
            return list(hit["sources"])
    sources = collect_all_source_files(
        str(RITZUNIT_MAIN), project_root=str(RITZUNIT_ROOT),
        dependencies=deps, source_roots=roots)
    if memo is not None:
        build.closure_memo_put(memo, {"sources": sources}, sources)
    return sources


def _as_object(path: str, tmpdir: str) -> Tuple[Optional[str], Optional[str]]:
    """An object file for `path`: itself if already one, else `clang -c` of the .ll."""
    if path.endswith(".o"):
        return path, None
    obj = os.path.join(tmpdir, Path(path).stem + ".rzu.o")
    error = _build_module().compile_ll_to_obj(Path(path), Path(obj), Path(path))
    return (None, error) if error else (obj, None)


def build_runner_objects(tmpdir: str, ll_cache: dict, test_modules=(),
                         compiler: str = "ritz0") -> Tuple[List[str], Optional[str]]:
    """Objects that make ritzunit the test binary's `main`.

    Every module the runner needs and the test does not (`test_modules`:
    the test's own dependency sources) is combined with `ld -r`, and every
    symbol but `main` is made local (`objcopy -G main`). Dependency objects
    are compiled with external linkage throughout, and the runner brings
    names the program may define too: its own `run_tests`, `parse_args`,
    `json_record_pass`, `g_verbose` (spire, http), and the ritzlib modules
    only it imports (ritzlib.string's `string_contains`; mausoleum defines
    one). Localized, none of them can clash with the program.

    A module the test imports as well stays an ordinary global object, linked
    once and shared: `ll_cache` is shared with the test's dependencies, so it
    is not compiled twice either.

    Returns (objects, error).
    """
    deps, _roots = _ritzunit_import_context()
    try:
        sources = _ritzunit_sources()
    except Exception as e:  # noqa: BLE001 -- reported as the file's failure
        return [], f"ritzunit import resolution failed: {e}"
    compiled, error = compile_dependencies(
        [Path(f) for f in sources], tmpdir, ll_cache,
        dependencies=deps, project_root=RITZUNIT_ROOT, compiler=compiler)
    if error:
        return [], f"ritzunit: {error}"

    shared_with_test = {Path(m).resolve() for m in test_modules}
    own, shared = [], []
    for src, out in zip(sources, compiled):
        if Path(src).resolve() not in shared_with_test:
            obj, error = _as_object(out, tmpdir)
            if error:
                return [], f"ritzunit: {error}"
            own.append(obj)
        else:
            shared.append(out)

    runner = os.path.join(tmpdir, "ritzunit_runner.o")
    for cmd in (["ld", "-r", "-o", runner, *own],
                ["objcopy", "--keep-global-symbol=main", runner]):
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return [], f"ritzunit: {cmd[0]} failed: {result.stderr}"
    return shared + [runner], None


def build_test_binary(source_path: str, tmpdir: str,
                      compiler: str = "ritz0") -> Tuple[Optional[str], Optional[str]]:
    """Compile and link `source_path`'s test binary in `tmpdir` with `compiler`.

    Every object in it, ritzunit's included, is built by `compiler`.

    Returns (exe_path, error).
    """
    project_root, dep_files, error, dependencies = setup_test_environment(source_path, tmpdir)
    if error:
        return None, error

    ll_cache = {}
    dep_objects, error = compile_dependencies(
        dep_files or [], tmpdir, ll_cache,
        dependencies=dependencies, project_root=project_root, compiler=compiler)
    if error:
        return None, error

    runner_objects, error = build_runner_objects(tmpdir, ll_cache, dep_files or [], compiler)
    if error:
        return None, error

    # The file's own `main` is dropped by test mode; for ritz0 it is stripped
    # here too because it is not part of what is being tested and need not
    # compile. ritz1 resolves imports from the file's own directory first, so
    # it compiles the file in place; it drops `main` before emitting anything.
    harness_ll = os.path.join(tmpdir, "test_main.ll")
    if compiler == "ritz0":
        harness_path = os.path.join(tmpdir, "test_main.ritz")
        Path(harness_path).write_text(strip_main_from_source(Path(source_path).read_text()))
    else:
        harness_path = str(Path(source_path).resolve())
    error = _harness_ll(source_path, harness_path, harness_ll, project_root, dependencies,
                        [Path(f) for f in dep_files or []], compiler)
    if error:
        return None, error

    # A module both the test and ritzunit import is in both lists once.
    objects = list(dict.fromkeys(dep_objects + runner_objects))
    return _link(objects + [harness_ll], os.path.join(tmpdir, "test"))


def _indent(text: str) -> str:
    return text.rstrip("\n").replace("\n", "\n      ")


def failures_from_report(report: dict) -> List[str]:
    """One message per test that did not pass, as `ritz0 --test` prints them."""
    failures = []
    for t in report.get("tests", []):
        status = t.get("status")
        if status == "pass":
            continue
        name = t.get("name", "?")
        if status == "crash":
            msg = f"{name}: crashed with signal {t.get('signal', '?')}"
        elif status == "timeout":
            msg = f"{name}: timeout"
        else:
            msg = f"{name}: exited with code {t.get('exit_code', '?')}"
        output = t.get("output", "")
        if output.strip():
            msg += "\n      " + _indent(output)
        failures.append(msg)
    return failures


def run_test_binary(exe_path: str, cwd: Optional[str] = None) -> Tuple[int, int, List[str]]:
    """Run a test binary once; return (passed, failed, failure_messages).

    ritzunit exits 0 when every test passed and 1 otherwise; anything else, or
    a report that does not parse, means the runner itself failed.
    """
    timeout = int(os.environ.get("RITZ_TEST_TIMEOUT", "180"))
    try:
        result = subprocess.run([exe_path] + runner_args(), capture_output=True,
                                timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired:
        return 0, 1, [f"test binary timed out after {timeout}s"]
    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    try:
        report = json.loads(result.stdout.decode("utf-8", errors="replace"))
        summary = report["summary"]
    except (ValueError, KeyError, TypeError):
        report = None
    if report is None or result.returncode not in (0, 1):
        msg = f"test runner exited with code {result.returncode} without a report"
        if stderr:
            msg += "\n      " + _indent(stderr)
        return 0, 1, [msg]
    passed = summary["passed"]
    failed = summary["failed"] + summary["crashed"] + summary["timeout"]
    failures = failures_from_report(report)
    if (failed > 0) != (result.returncode == 1):
        failures.append(f"test runner exit code {result.returncode} disagrees with "
                        f"its report ({failed} failed)")
        failed = max(failed, 1)
    return passed, failed, failures


def run_test_file(source_path: str, verbose: bool = False,
                  compiler: str = "ritz0") -> Tuple[int, int, List[str]]:
    """Build `source_path`'s test binary with `compiler` and run it.

    Returns (passed, failed, failure_messages). A file whose binary cannot be
    built fails every one of its tests with the build error.
    """
    tests = find_test_functions(source_path)
    if not tests:
        return (0, 0, [])

    tmpdir = None
    try:
        tmpdir = make_scratch_dir()
        if verbose:
            print(f"  Building test binary for {len(tests)} tests...", flush=True)
        exe_path, error = build_test_binary(source_path, tmpdir, compiler)
        if error:
            return 0, len(tests), [f"{name}: {error}" for name, _fn in tests]
        passed, failed, failures = run_test_binary(exe_path)
        if verbose:
            for f in failures:
                print(f"  FAIL {f}")
        return passed, failed, failures
    finally:
        if tmpdir and os.path.exists(tmpdir):
            cleanup_scratch_dir(tmpdir)


def run_files(files: List[str], verbose: bool = False, compiler: str = "ritz0") -> int:
    """Run test files; print the report `ritz0 --test` prints; its exit code.

    The report ends with "N passed, M failed", which build.py's
    classify_test_file reads, so `ritz0 --test` and build.py's in-process
    unit (AGAST #1915) must share this one printer.
    """
    total_passed = 0
    total_failed = 0
    all_failures = []

    for file_path in files:
        if verbose:
            print(f"\n{file_path}:")
        try:
            passed, failed, failures = run_test_file(file_path, verbose, compiler)
            total_passed += passed
            total_failed += failed
            all_failures.extend(failures)
        except Exception as e:  # noqa: BLE001 -- the file's verdict, not a crash
            print(f"Error in {file_path}: {e}", file=sys.stderr)
            total_failed += 1
            all_failures.append(f"{file_path}: error")

    print(f"\n{total_passed} passed, {total_failed} failed")

    if all_failures:
        print("\nFailures:")
        for f in all_failures:
            print(f"  - {f}")

    return 0 if total_failed == 0 else 1


def main():
    parser = argparse.ArgumentParser(description='Ritz Test Runner')
    parser.add_argument('files', nargs='+', help='Test files to run')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()

    # AGAST #1392: turn SIGTERM/SIGINT into an unwind so the `finally` blocks
    # below actually run. Installed after argument parsing so `--help` and a
    # usage error still behave like an ordinary CLI.
    install_signal_handlers()
    sys.exit(run_files(args.files, args.verbose))


if __name__ == '__main__':
    main()
