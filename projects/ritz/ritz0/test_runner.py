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
from typing import List, Tuple, Optional

from lexer import Lexer, LexerError
from parser import Parser, ParseError
from import_resolver import collect_all_source_files
import ritz_ast as rast


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


def compile_test(
    source_path: str,
    test_name: str,
    tmpdir: str,
    lib_files: List[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """Compile a single test to a binary using proper separate compilation.

    Args:
        source_path: Path to the test file
        test_name: Name of the test function to run
        tmpdir: Temporary directory for build artifacts
        lib_files: Optional additional library files

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

    # Copy helper files to temp directory so they can be found via relative imports
    # This includes test_import_*.ritz (legacy) and helpers.ritz (common pattern)
    test_dir = Path(source_path).parent
    for lib_file in test_dir.glob("test_import_*.ritz"):
        shutil.copy(lib_file, tmpdir)
    # Also copy helpers.ritz if it exists (common test helper module)
    helpers_file = test_dir / "helpers.ritz"
    if helpers_file.exists():
        shutil.copy(helpers_file, tmpdir)

    # Symlink project source directories (lib/, src/) to temp for import resolution
    # Find project root by looking for ritz.toml
    project_root = None
    search_dir = Path(source_path).parent.resolve()
    while search_dir != search_dir.parent:
        if (search_dir / "ritz.toml").exists():
            project_root = search_dir
            break
        search_dir = search_dir.parent

    if project_root:
        # Symlink common source directories so imports like 'lib.foo' work
        for src_dir in ["lib", "src", "ritzlib"]:
            src_path = project_root / src_dir
            # Follow symlinks to get the real path
            if src_path.exists():
                real_path = src_path.resolve()
                link_path = Path(tmpdir) / src_dir
                if not link_path.exists():
                    os.symlink(real_path, link_path)

    # Discover all source files through import resolution on the modified file
    try:
        source_files = collect_all_source_files(test_file_path, project_root=str(project_root) if project_root else None)
    except Exception as e:
        return None, f"Import resolution failed: {e}"

    # Add explicit lib files if provided (legacy support)
    if lib_files:
        for lib in lib_files:
            lib_path = Path(lib).resolve()
            if lib_path not in [Path(f).resolve() for f in source_files]:
                source_files.insert(-1, lib_path)

    ll_files = []

    # Compile each source file to LLVM IR
    # Main source (last in list) includes _start, dependencies don't
    for i, src in enumerate(source_files):
        is_main = (i == len(source_files) - 1)

        # Use a unique name to avoid collisions
        path_hash = hashlib.md5(str(src).encode()).hexdigest()[:8]
        src_name = f"{Path(src).stem}_{path_hash}"
        ll_path = os.path.join(tmpdir, f"{src_name}.ll")

        compile_cmd = [sys.executable, str(ritz0_py), str(src), "-o", ll_path]
        if not is_main:
            compile_cmd.append("--no-runtime")

        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None, f"ritz0 failed for {Path(src).name}: {result.stderr}"

        ll_files.append(ll_path)

    # Link all .ll files with clang
    # The main .ll already includes _start, so no external runtime needed
    # Use -march=native to enable CPU features like SIMD intrinsics (pclmul, sse4.2, etc.)
    exe_path = os.path.join(tmpdir, "test")
    clang_cmd = ["clang"] + ll_files + ["-o", exe_path, "-nostdlib", "-g", "-march=native"]
    result = subprocess.run(clang_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, f"clang failed: {result.stderr}"

    return exe_path, None


def run_test_file(source_path: str, verbose: bool = False, lib_files: List[str] = None) -> Tuple[int, int, List[str]]:
    """
    Run all tests in a file using proper separate compilation.
    Returns (passed, failed, failure_messages).
    """
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
            # Create temp directory manually so we can clean up symlinks properly
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


def main():
    parser = argparse.ArgumentParser(description='Ritz Test Runner')
    parser.add_argument('files', nargs='+', help='Test files to run')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-l', '--lib', action='append', default=[], help='Library files to include (can be specified multiple times)')

    args = parser.parse_args()

    total_passed = 0
    total_failed = 0
    all_failures = []

    for file_path in args.files:
        if args.verbose:
            print(f"\n{file_path}:")

        try:
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
