#!/usr/bin/env python3
"""
Ritz Test Runner

Discovers and runs @test functions in .ritz files using proper separate compilation.
Each test is compiled by appending a main() that calls the test function.
"""

import sys
import argparse
import subprocess
import tempfile
import hashlib
import os
import shutil
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from lexer import Lexer, LexerError
from parser import Parser, ParseError
from import_resolver import collect_all_source_files, DependencyMapping
import ritz_ast as rast

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11


def parse_ritz_toml_dependencies(toml_path: Path, pkg_dir: Path) -> Dict[str, DependencyMapping]:
    """Parse [dependencies] section from ritz.toml config.

    Also adds a self-reference for the current project so tests can import
    from their own package using the package name (e.g., import cryptosec.u128).

    Args:
        toml_path: Path to ritz.toml file
        pkg_dir: Package directory (parent of ritz.toml)

    Returns:
        Dict mapping dependency name to DependencyMapping
    """
    if not toml_path.exists():
        return {}

    with open(toml_path, "rb") as f:
        config = tomllib.load(f)

    deps = {}

    # Add self-reference for current project (Issue #48)
    # This allows tests to import from their own package using the package name
    # e.g., import cryptosec.u128 when running tests in cryptosec project
    pkg_name = config.get("package", {}).get("name")
    if pkg_name:
        # Determine sources for current project
        pkg_sources = config.get("sources")
        if pkg_sources is None:
            pkg_sources = config.get("package", {}).get("sources")
        if pkg_sources is None:
            pkg_sources = config.get("build", {}).get("sources")
        if pkg_sources is None:
            # Default: check for common source directories
            if (pkg_dir / "src").is_dir():
                pkg_sources = ["src"]
            elif (pkg_dir / "lib").is_dir():
                pkg_sources = ["lib"]
            else:
                pkg_sources = ["."]
        if isinstance(pkg_sources, str):
            pkg_sources = [pkg_sources]

        deps[pkg_name] = DependencyMapping(name=pkg_name, path=pkg_dir.resolve(), sources=pkg_sources)
    deps_config = config.get("dependencies", {})

    for name, spec in deps_config.items():
        if isinstance(spec, dict):
            # Full spec: { path = "...", sources = [...] }
            dep_path = spec.get("path")
            if dep_path is None:
                continue

            # Resolve path relative to package directory
            dep_path = (pkg_dir / dep_path).resolve()
            if not dep_path.exists():
                continue

            # Get sources from dependency's ritz.toml if not specified
            sources = spec.get("sources")
            if sources is None:
                dep_toml = dep_path / "ritz.toml"
                if dep_toml.exists():
                    with open(dep_toml, "rb") as f:
                        dep_config = tomllib.load(f)
                    # Check multiple locations for sources
                    sources = dep_config.get("sources")
                    if sources is None:
                        sources = dep_config.get("package", {}).get("sources")
                    if sources is None:
                        sources = dep_config.get("build", {}).get("sources")
                    if sources is None:
                        # Default to ["src"], but also check root if src doesn't exist
                        if (dep_path / "src").is_dir():
                            sources = ["src"]
                        else:
                            sources = ["."]  # Source files at root level
                else:
                    # No ritz.toml - check if src/ exists, otherwise assume root level
                    if (dep_path / "src").is_dir():
                        sources = ["src"]
                    else:
                        sources = ["."]  # Source files at root level (like ritzlib)

            if isinstance(sources, str):
                sources = [sources]

            deps[name] = DependencyMapping(name=name, path=dep_path, sources=sources)
        elif isinstance(spec, str):
            # Shorthand: just a path
            dep_path = (pkg_dir / spec).resolve()
            if not dep_path.exists():
                continue
            deps[name] = DependencyMapping(name=name, path=dep_path, sources=["src"])

    return deps


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
    if project_root:
        toml_path = project_root / "ritz.toml"
        dependencies = parse_ritz_toml_dependencies(toml_path, project_root)

    if project_root:
        # Symlink common source directories
        for src_dir in ["lib", "src", "ritzlib"]:
            src_path = project_root / src_dir
            if src_path.exists():
                real_path = src_path.resolve()
                link_path = Path(tmpdir) / src_dir
                if not link_path.exists():
                    os.symlink(real_path, link_path)

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
            dependencies=dependencies if dependencies else None
        )
        # Remove the dummy harness from the list
        source_files = [f for f in source_files if Path(f).name != "dummy_harness.ritz"]
        return project_root, source_files, None, dependencies
    except Exception as e:
        return None, None, f"Import resolution failed: {e}", None


def compile_dependencies(
    source_files: List[Path],
    tmpdir: str,
    ll_cache: dict,
    dependencies: Dict[str, DependencyMapping] = None,
    project_root: Path = None
) -> Tuple[List[str], Optional[str]]:
    """Compile dependencies to LLVM IR, using cache when possible.

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

    for src in source_files:
        src_key = str(Path(src).resolve())

        # Check cache first
        if src_key in ll_cache:
            ll_files.append(ll_cache[src_key])
            continue

        # Compile to .ll
        path_hash = hashlib.md5(src_key.encode()).hexdigest()[:8]
        src_name = f"{Path(src).stem}_{path_hash}"
        ll_path = os.path.join(tmpdir, f"{src_name}.ll")

        compile_cmd = [sys.executable, str(ritz0_py), str(src), "-o", ll_path, "--no-runtime"]

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

        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None, f"ritz0 failed for {Path(src).name}: {result.stderr}"

        ll_cache[src_key] = ll_path
        ll_files.append(ll_path)

    return ll_files, None


def compile_test(
    source_path: str,
    test_name: str,
    tmpdir: str,
    lib_files: List[str] = None,
    ll_cache: dict = None,
    dep_ll_files: List[str] = None,
    project_root: Path = None,
    dependencies: Dict[str, DependencyMapping] = None
) -> Tuple[Optional[str], Optional[str]]:
    """Compile a single test to a binary using proper separate compilation.

    Args:
        source_path: Path to the test file
        test_name: Name of the test function to run
        tmpdir: Temporary directory for build artifacts
        lib_files: Optional additional library files
        ll_cache: Optional cache of compiled .ll files (for reuse across tests)
        dep_ll_files: Pre-compiled dependency .ll files (if already compiled)
        project_root: Project root (if already determined)
        dependencies: ritz.toml dependency mappings for import resolution

    Returns:
        (exe_path, error_message) - exe_path is None on failure
    """
    ritz0_dir = Path(__file__).parent
    ritz0_py = ritz0_dir / "ritz0.py"

    # Read original source and strip any existing main
    original_source = Path(source_path).read_text()
    source_no_main = strip_main_from_source(original_source)

    # Create test harness source by appending main that calls the test
    harness_source = source_no_main + f"""

fn main() -> i32
  {test_name}()
"""

    # Write the modified test source to temp
    test_file_path = os.path.join(tmpdir, "test_main.ritz")
    Path(test_file_path).write_text(harness_source)

    # If we have pre-compiled dependencies, just compile the harness
    if dep_ll_files is not None:
        import json as json_module
        ll_files = list(dep_ll_files)

        # Compile the test harness (with runtime since it has main)
        harness_hash = hashlib.md5(test_name.encode()).hexdigest()[:8]
        harness_ll = os.path.join(tmpdir, f"harness_{harness_hash}.ll")

        compile_cmd = [sys.executable, str(ritz0_py), test_file_path, "-o", harness_ll]

        # Pass dependencies to ritz0 for harness compilation (Issue #48)
        if dependencies:
            deps_json = {
                name: {"path": str(spec.path), "sources": spec.sources}
                for name, spec in dependencies.items()
            }
            compile_cmd.extend(["--deps", json_module.dumps(deps_json)])

        # Pass project root for import resolution
        if project_root:
            compile_cmd.extend(["--project-root", str(project_root)])

        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None, f"ritz0 failed for harness: {result.stderr}"

        ll_files.append(harness_ll)
    else:
        # Legacy path: compile everything from scratch
        # Copy helper files to temp directory
        test_dir = Path(source_path).parent
        for lib_file in test_dir.glob("test_import_*.ritz"):
            shutil.copy(lib_file, tmpdir)
        helpers_file = test_dir / "helpers.ritz"
        if helpers_file.exists():
            shutil.copy(helpers_file, tmpdir)

        # Find project root if not provided
        if project_root is None:
            search_dir = Path(source_path).parent.resolve()
            while search_dir != search_dir.parent:
                if (search_dir / "ritz.toml").exists():
                    project_root = search_dir
                    break
                search_dir = search_dir.parent

        if project_root:
            for src_dir in ["lib", "src", "ritzlib"]:
                src_path = project_root / src_dir
                if src_path.exists():
                    real_path = src_path.resolve()
                    link_path = Path(tmpdir) / src_dir
                    if not link_path.exists():
                        os.symlink(real_path, link_path)

        # Parse dependencies from ritz.toml if not provided
        if dependencies is None and project_root:
            toml_path = project_root / "ritz.toml"
            dependencies = parse_ritz_toml_dependencies(toml_path, project_root)

        try:
            source_files = collect_all_source_files(
                test_file_path,
                project_root=str(project_root) if project_root else None,
                dependencies=dependencies if dependencies else None
            )
        except Exception as e:
            return None, f"Import resolution failed: {e}"

        if lib_files:
            for lib in lib_files:
                lib_path = Path(lib).resolve()
                if lib_path not in [Path(f).resolve() for f in source_files]:
                    source_files.insert(-1, lib_path)

        ll_files = []
        if ll_cache is None:
            ll_cache = {}

        for i, src in enumerate(source_files):
            is_main = (i == len(source_files) - 1)
            src_key = str(Path(src).resolve())

            if not is_main and src_key in ll_cache:
                ll_files.append(ll_cache[src_key])
                continue

            path_hash = hashlib.md5(src_key.encode()).hexdigest()[:8]
            src_name = f"{Path(src).stem}_{path_hash}"
            ll_path = os.path.join(tmpdir, f"{src_name}.ll")

            compile_cmd = [sys.executable, str(ritz0_py), str(src), "-o", ll_path]
            if not is_main:
                compile_cmd.append("--no-runtime")

            result = subprocess.run(compile_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return None, f"ritz0 failed for {Path(src).name}: {result.stderr}"

            if not is_main:
                ll_cache[src_key] = ll_path
            ll_files.append(ll_path)

    # Link all .ll files with clang
    exe_path = os.path.join(tmpdir, "test")
    clang_cmd = ["clang"] + ll_files + ["-o", exe_path, "-nostdlib", "-g", "-march=native"]
    result = subprocess.run(clang_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, f"clang failed: {result.stderr}"

    return exe_path, None


def run_test_file(source_path: str, verbose: bool = False, lib_files: List[str] = None) -> Tuple[int, int, List[str]]:
    """
    Run all tests in a file using proper separate compilation.

    OPTIMIZED: Compiles dependencies ONCE and reuses them for all tests in the file.
    This is ~10-20x faster for files with many tests and complex dependency trees.

    Returns (passed, failed, failure_messages).
    """
    tests = find_test_functions(source_path)
    if not tests:
        return (0, 0, [])

    passed = 0
    failed = 0
    failures = []

    # Create a SINGLE temp directory for all tests in this file
    # This allows us to cache compiled .ll files across tests
    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp(dir='.')

        # Step 1: Set up environment and discover dependencies ONCE
        if verbose:
            print(f"  Compiling dependencies for {len(tests)} tests...", flush=True)

        project_root, dep_files, error, dependencies = setup_test_environment(source_path, tmpdir)
        if error:
            # Fall back to per-test compilation on setup error
            if verbose:
                print(f"  Warning: {error}, falling back to per-test compilation")
            cleanup_tmpdir_with_symlinks(tmpdir)
            return _run_test_file_legacy(source_path, verbose, lib_files)

        # Step 2: Compile all dependencies ONCE
        ll_cache = {}
        dep_ll_files, error = compile_dependencies(
            dep_files or [], tmpdir, ll_cache,
            dependencies=dependencies,
            project_root=project_root
        )
        if error:
            if verbose:
                print(f"  Warning: {error}, falling back to per-test compilation")
            cleanup_tmpdir_with_symlinks(tmpdir)
            return _run_test_file_legacy(source_path, verbose, lib_files)

        # Step 3: Run each test (only need to compile harness + link)
        for test_name, test_fn in tests:
            if verbose:
                print(f"  Running {test_name}...", end=" ", flush=True)

            try:
                exe_path, error = compile_test(
                    source_path,
                    test_name,
                    tmpdir,
                    lib_files,
                    ll_cache=ll_cache,
                    dep_ll_files=dep_ll_files,
                    project_root=project_root,
                    dependencies=dependencies  # Issue #48: Pass dependencies for import resolution
                )

                if error:
                    failed += 1
                    failures.append(f"{test_name}: {error}")
                    if verbose:
                        print("FAIL (compile)")
                    continue

                # Run the test
                result = subprocess.run([exe_path], capture_output=True, timeout=10)
                if result.returncode == 0:
                    passed += 1
                    if verbose:
                        print("OK")
                else:
                    failed += 1
                    failures.append(f"{test_name}: exited with code {result.returncode}")
                    if verbose:
                        print(f"FAIL (exit {result.returncode})")

            except subprocess.TimeoutExpired:
                failed += 1
                failures.append(f"{test_name}: timeout")
                if verbose:
                    print("FAIL (timeout)")
            except Exception as e:
                failed += 1
                failures.append(f"{test_name}: {e}")
                if verbose:
                    print(f"FAIL ({e})")

    finally:
        # Clean up temp directory with proper symlink handling
        if tmpdir and os.path.exists(tmpdir):
            cleanup_tmpdir_with_symlinks(tmpdir)

    return (passed, failed, failures)


def _run_test_file_legacy(source_path: str, verbose: bool = False, lib_files: List[str] = None) -> Tuple[int, int, List[str]]:
    """Legacy per-test compilation (fallback when optimized path fails)."""
    tests = find_test_functions(source_path)
    if not tests:
        return (0, 0, [])

    passed = 0
    failed = 0
    failures = []

    for test_name, test_fn in tests:
        if verbose:
            print(f"  Running {test_name}...", end=" ", flush=True)

        tmpdir = None
        try:
            tmpdir = tempfile.mkdtemp(dir='.')
            exe_path, error = compile_test(
                source_path,
                test_name,
                tmpdir,
                lib_files
            )

            if error:
                failed += 1
                failures.append(f"{test_name}: {error}")
                if verbose:
                    print("FAIL (compile)")
                continue

            result = subprocess.run([exe_path], capture_output=True, timeout=10)
            if result.returncode == 0:
                passed += 1
                if verbose:
                    print("OK")
            else:
                failed += 1
                failures.append(f"{test_name}: exited with code {result.returncode}")
                if verbose:
                    print(f"FAIL (exit {result.returncode})")

        except subprocess.TimeoutExpired:
            failed += 1
            failures.append(f"{test_name}: timeout")
            if verbose:
                print("FAIL (timeout)")
        except Exception as e:
            failed += 1
            failures.append(f"{test_name}: {e}")
            if verbose:
                print(f"FAIL ({e})")
        finally:
            if tmpdir and os.path.exists(tmpdir):
                cleanup_tmpdir_with_symlinks(tmpdir)

    return (passed, failed, failures)


def run_batch_tests(
    test_files: List[str],
    verbose: bool = False,
    project_root: str = None,
    ritzunit_dir: str = None
) -> int:
    """Run all tests in batch mode using ritzunit's ELF-based test discovery.

    This compiles all dependencies ONCE and links all test files into a single
    binary with ritzunit's runner. Much faster than per-test compilation.

    Args:
        test_files: List of test file paths
        verbose: Show verbose output
        project_root: Project root for import resolution
        ritzunit_dir: Path to ritzunit project (for runner.ritz)

    Returns:
        Exit code (0 = all passed)
    """
    if not test_files:
        print("No test files specified")
        return 1

    ritz0_dir = Path(__file__).parent
    ritz0_py = ritz0_dir / "ritz0.py"
    list_deps_py = ritz0_dir / "list_deps.py"

    # Find ritzunit if not specified
    if ritzunit_dir is None:
        # Look relative to ritz0 directory
        # ritz0 is at: projects/ritz/ritz0
        # ritzunit is at: projects/ritzunit
        # So: ritz0_dir.parent = projects/ritz, .parent = projects, /ritzunit
        ritzunit_dir = ritz0_dir.parent.parent / "ritzunit"
        if not ritzunit_dir.exists():
            # Try RITZ_PATH
            ritz_path = os.environ.get("RITZ_PATH")
            if ritz_path:
                ritzunit_dir = Path(ritz_path) / "ritzunit"

    if not ritzunit_dir or not ritzunit_dir.exists():
        print(f"Error: ritzunit not found. Set RITZ_PATH or ensure projects/ritzunit exists.", file=sys.stderr)
        return 1

    runner_path = ritzunit_dir / "src" / "runner.ritz"
    if not runner_path.exists():
        print(f"Error: ritzunit runner not found at {runner_path}", file=sys.stderr)
        return 1

    # Find project root from first test file
    if project_root is None:
        test_path = Path(test_files[0]).resolve()
        search_dir = test_path.parent
        while search_dir != search_dir.parent:
            if (search_dir / "ritz.toml").exists():
                project_root = str(search_dir)
                break
            search_dir = search_dir.parent

    tmpdir = None
    try:
        tmpdir = tempfile.mkdtemp(prefix="ritz_batch_test_")

        # Step 1: Collect all dependencies from the runner (includes ritzlib, reporter, etc.)
        if verbose:
            print("Collecting runner dependencies...")

        result = subprocess.run(
            [sys.executable, str(list_deps_py), str(runner_path),
             "--project-root", str(ritzunit_dir)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Error collecting runner dependencies: {result.stderr}", file=sys.stderr)
            return 1

        runner_deps = [Path(f.strip()) for f in result.stdout.strip().split('\n') if f.strip()]

        # Step 2: Collect all source files from test files (excluding duplicates)
        all_sources = set()
        for tf in test_files:
            result = subprocess.run(
                [sys.executable, str(list_deps_py), str(tf),
                 "--project-root", project_root or str(Path(tf).parent)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"Error collecting deps for {tf}: {result.stderr}", file=sys.stderr)
                return 1

            for f in result.stdout.strip().split('\n'):
                if f.strip():
                    all_sources.add(Path(f.strip()).resolve())

        # Add runner dependencies
        for dep in runner_deps:
            all_sources.add(dep.resolve())

        # Add test files themselves
        for tf in test_files:
            all_sources.add(Path(tf).resolve())

        # Convert to list and sort (runner.ritz should be last - it has main())
        source_list = sorted(all_sources, key=lambda p: (p == runner_path.resolve(), str(p)))

        if verbose:
            print(f"Compiling {len(source_list)} source files...")

        # Step 3: Compile each source file ONCE
        ll_files = []
        compiled = {}  # Track by resolved path to avoid duplicates

        for src in source_list:
            src_resolved = src.resolve()
            if str(src_resolved) in compiled:
                ll_files.append(compiled[str(src_resolved)])
                continue

            is_runner = (src_resolved == runner_path.resolve())

            # Use path hash for unique names
            path_hash = hashlib.md5(str(src_resolved).encode()).hexdigest()[:8]
            src_name = f"{src.stem}_{path_hash}"
            ll_path = os.path.join(tmpdir, f"{src_name}.ll")

            # All files compiled with --no-runtime except runner (which has main)
            compile_cmd = [sys.executable, str(ritz0_py), str(src), "-o", ll_path]
            if not is_runner:
                compile_cmd.append("--no-runtime")

            result = subprocess.run(compile_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error compiling {src.name}: {result.stderr}", file=sys.stderr)
                return 1

            ll_files.append(ll_path)
            compiled[str(src_resolved)] = ll_path

        # Step 4: Link everything with clang
        if verbose:
            print(f"Linking {len(ll_files)} object files...")

        exe_path = os.path.join(tmpdir, "test_runner")
        clang_cmd = ["clang"] + ll_files + ["-o", exe_path, "-nostdlib", "-g", "-march=native"]
        result = subprocess.run(clang_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error linking: {result.stderr}", file=sys.stderr)
            return 1

        # Step 5: Run the test binary
        if verbose:
            print(f"Running tests...")

        run_cmd = [exe_path]
        if verbose:
            run_cmd.append("-v")

        result = subprocess.run(run_cmd, capture_output=False)
        return result.returncode

    except Exception as e:
        print(f"Error in batch test: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if tmpdir and os.path.exists(tmpdir):
            cleanup_tmpdir_with_symlinks(tmpdir)


def main():
    parser = argparse.ArgumentParser(description='Ritz Test Runner')
    parser.add_argument('files', nargs='+', help='Test files to run')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-l', '--lib', action='append', default=[], help='Library files to include (can be specified multiple times)')
    parser.add_argument('--batch', action='store_true',
                        help='Use batch mode: compile once, run all tests via ritzunit (much faster)')
    parser.add_argument('--project-root', help='Project root for import resolution')
    parser.add_argument('--legacy', action='store_true',
                        help='Use legacy per-test compilation (for benchmarking)')

    args = parser.parse_args()

    # Use batch mode if requested
    if args.batch:
        sys.exit(run_batch_tests(
            args.files,
            verbose=args.verbose,
            project_root=args.project_root
        ))

    # Optimized per-test mode with dependency caching (default)
    total_passed = 0
    total_failed = 0
    all_failures = []

    for file_path in args.files:
        if args.verbose:
            print(f"\n{file_path}:")

        try:
            if args.legacy:
                passed, failed, failures = _run_test_file_legacy(file_path, args.verbose, args.lib)
            else:
                passed, failed, failures = run_test_file(file_path, args.verbose, args.lib)
            total_passed += passed
            total_failed += failed
            all_failures.extend(failures)
        except (LexerError, ParseError) as e:
            print(f"Error in {file_path}: {e}", file=sys.stderr)
            total_failed += 1
            all_failures.append(f"{file_path}: parse error")

    # Summary
    print(f"\n{total_passed} passed, {total_failed} failed")

    if all_failures:
        print("\nFailures:")
        for f in all_failures:
            print(f"  - {f}")

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == '__main__':
    main()
