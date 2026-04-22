#!/usr/bin/env python3
"""
ritz0 - The Ritz Bootstrap Compiler

A minimal compiler written in Python that compiles Ritz source to LLVM IR.
This is used to bootstrap the self-hosted ritz1 compiler.

Usage:
    python ritz0.py <source.ritz> -o <output.ll>

Compilation Model:
    - One input file → one output file (1:1)
    - Imports are resolved and emitted as `declare` (external references)
    - Local definitions are emitted as `define` (full bodies)
    - Linking is a separate step (use llc + ld)
"""

import sys
import argparse
from pathlib import Path

from lexer import Lexer, LexerError
# Use generated parser with adapter (comment out to use hand-written parser)
# from parser_adapter import Parser, ParseError  # Generated parser
from parser import Parser, ParseError  # Hand-written parser
from emitter_llvmlite import emit as emit_llvmlite, get_test_functions, generate_test_main_source
from import_resolver import resolve_imports, ImportError as RitzImportError
from name_resolver import resolve_names, NameError as RitzNameError
from move_checker import MoveChecker, OwnershipError
from type_checker import TypeChecker, TypeError as RitzTypeError
from const_eval import evaluate_array_sizes, ConstEvalError
from emitter.fn_cache import (
    source_file_hash, build_hash_map, build_sig_hash_map,
    read_sig_file, write_sig_file, check_cache, check_source_hash,
    build_sig_data, detect_sig_changes, invalidate_dependents,
)
import ritz_ast as rast


def _filter_by_target_os(module: rast.Module, target_os: str) -> rast.Module:
    """Filter out items that don't match the target OS.

    Items with [[target_os = "..."]] attribute are only included if the
    attribute value matches the current target_os. Items without the
    attribute are always included.

    Args:
        module: The module to filter
        target_os: The target OS to match (e.g., "linux", "harland")

    Returns:
        A new module with only matching items
    """
    filtered_items = []
    for item in module.items:
        # Check if item has target_os attribute via get_attr_value method
        if hasattr(item, 'get_attr_value'):
            item_target_os = item.get_attr_value('target_os')
            if item_target_os is not None and item_target_os != target_os:
                # Skip items that don't match target_os
                continue
        filtered_items.append(item)

    # Create new module with filtered items
    return rast.Module(module.span, filtered_items)


def compile_file(source_path: str, output_path: str, no_runtime: bool = False,
                  check_names: bool = False, check_ownership: bool = False,
                  check_types: bool = False, dependencies: dict = None,
                  source_roots: list = None, project_root: str = None,
                  target: str = 'x86_64-unknown-linux-gnu',
                  target_os: str = 'linux') -> bool:
    """Compile a single Ritz source file to LLVM IR.

    This is the only compilation mode. Each .ritz file compiles to one .ll file.
    Imports are resolved and emitted as external declarations for linking.

    Args:
        source_path: Path to the source .ritz file
        output_path: Output .ll file path
        no_runtime: Don't emit _start entry point (for library modules)
        check_names: Verify all referenced names are defined before IR emission
        check_ownership: Check ownership/borrowing rules before IR emission
        check_types: Check types are compatible before IR emission
        dependencies: RFC #109 dependency mappings for namespace resolution
        source_roots: List of source directories to search for imports
        project_root: Explicit project root for import resolution (source roots relative to this)
        target: Target triple (default: x86_64-unknown-linux-gnu)
        target_os: Target OS for conditional compilation (default: linux)
    """
    try:
        # Read source file
        source = Path(source_path).read_text()

        # Get absolute path for source file tracking
        source_abs_path = str(Path(source_path).resolve())

        # --- Incremental compilation: source-file-level hash check ---
        # If the .ll output exists, is newer than the source, and the
        # source hash matches the cached hash in .ritz.sig, skip everything.
        output_file = Path(output_path)
        if output_file.exists():
            source_mtime = Path(source_path).stat().st_mtime
            output_mtime = output_file.stat().st_mtime
            if output_mtime >= source_mtime and check_source_hash(source, source_abs_path):
                print(f"Skipped {source_path} (unchanged)")
                return True

        # Extract directory and filename for debug info
        source_path_obj = Path(source_path)
        source_file = source_path_obj.name
        source_dir = str(source_path_obj.parent.resolve()) if source_path_obj.parent else "."

        # Lex
        lexer = Lexer(source, source_path)
        tokens = lexer.tokenize()

        # Parse
        # Note: Parser may accept source= kwarg (needed for generated parser adapter)
        try:
            parser = Parser(tokens, source=source)
        except TypeError:
            parser = Parser(tokens)
        module = parser.parse_module()

        # Resolve imports (recursively parse and merge imported modules)
        # Note: use_cache=False because the cache creates stub functions without bodies,
        # which is incompatible with our current merged-module architecture.
        # For separate compilation, the cache would be appropriate.
        module = resolve_imports(module, source_path, project_root=project_root, use_cache=False, dependencies=dependencies, source_roots=source_roots)

        # Filter out items that don't match target_os
        # This must happen after import resolution but before name resolution
        # so that name resolution doesn't see excluded items
        module = _filter_by_target_os(module, target_os)

        # Evaluate constant expressions in array sizes
        # This must happen before name resolution since it transforms the AST
        const_errors = evaluate_array_sizes(module)
        if const_errors:
            for err in const_errors:
                print(f"Const eval error: {err}", file=sys.stderr)
            return False

        # Name resolution check (verifies all referenced names are defined)
        if check_names:
            name_errors = resolve_names(module)
            if name_errors:
                for err in name_errors:
                    print(f"Name error: {err}", file=sys.stderr)
                return False

        # Type check (verifies type compatibility)
        if check_types:
            type_checker = TypeChecker()
            type_errors = type_checker.check(module)
            if type_errors:
                for err in type_errors:
                    print(f"Type error: {err}", file=sys.stderr)
                return False

        # Ownership check (verifies move/borrow rules)
        if check_ownership:
            checker = MoveChecker()
            ownership_errors = checker.check(module)
            if ownership_errors:
                for err in ownership_errors:
                    print(f"Ownership error: {err}", file=sys.stderr)
                return False

        # --- Incremental compilation: per-fn IR reuse ---
        # Build hash map and check against cached data before emission
        fn_cache_data = None
        try:
            fn_hashes = build_hash_map(source, source_abs_path)
            sig_hashes = build_sig_hash_map(source, source_abs_path)
            old_sig_data = read_sig_file(source_abs_path)

            # Detect signature changes and invalidate dependent modules
            changed_sigs = detect_sig_changes(source_abs_path, sig_hashes)
            if changed_sigs:
                project_root = str(Path(source_path).resolve().parent)
                for parent in Path(source_path).resolve().parents:
                    if (parent / '.git').exists() or (parent / 'ritzlib').is_dir():
                        project_root = str(parent)
                        break
                invalidate_dependents(source_abs_path, changed_sigs, project_root)

            # Check which functions have cached IR
            hits, misses = check_cache(fn_hashes, old_sig_data)
            fn_cache_data = {
                'cache_hits': hits,
                'cache_misses': misses,
                'sig_data': old_sig_data,
            }
        except Exception:
            fn_hashes = {}
            sig_hashes = {}
            old_sig_data = None

        # Emit IR
        # Always use separate compilation: each source file → one .ll file
        # Functions from current file: define (full body)
        # Functions from imports: declare (external reference)
        # --no-runtime only controls whether to emit _start entry point
        emit_result = emit_llvmlite(module, no_runtime=no_runtime,
                           source_file=source_file, source_dir=source_dir,
                           main_source_path=source_abs_path,
                           target=target, target_os=target_os,
                           fn_cache_data=fn_cache_data)

        if fn_cache_data is not None and isinstance(emit_result, tuple):
            ir, emitted_fn_ir = emit_result
        else:
            ir = emit_result
            emitted_fn_ir = {}

        # Write output
        Path(output_path).write_text(ir)

        # --- Write .ritz.sig cache with emitted function IR ---
        try:
            # Extract import paths from the module for the sig file
            import_paths = []
            for item in module.items:
                if isinstance(item, rast.Import):
                    import_paths.append('.'.join(item.path))

            sig_data = build_sig_data(
                source=source,
                fn_hashes=fn_hashes,
                sig_hashes=sig_hashes,
                fn_ir=emitted_fn_ir,
                imports=import_paths,
                old_sig_data=old_sig_data,
            )
            write_sig_file(source_abs_path, sig_data)
        except Exception as e:
            # Cache write failure is non-fatal
            print(f"Warning: cache write failed: {e}", file=sys.stderr)

        print(f"Compiled {source_path} -> {output_path}")
        return True

    except LexerError as e:
        print(f"Lexer error: {e}", file=sys.stderr)
        return False
    except ParseError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return False
    except RitzImportError as e:
        print(f"Import error: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Compiler error: {e}", file=sys.stderr)
        raise


def discover_tests(test_dir: str = "test") -> list:
    """Discover all test files in a directory, sorted by level."""
    test_path = Path(test_dir)
    if not test_path.exists():
        return []

    test_files = sorted(test_path.glob("test_level*.ritz"))
    return [str(f) for f in test_files]


def emit_test_main(source_paths: list, output_path: str) -> bool:
    """Generate a test main that runs all @test functions from given source files.

    This parses all source files, finds @test functions, and generates a main()
    that uses ritzlib/testing.ritz to run them all.

    Args:
        source_paths: List of source file paths to scan for @test functions
        output_path: Output path for the generated test main source
    """
    from ritz_ast import Module, Item
    import ritz_ast as rast

    all_test_fns = []

    for source_path in source_paths:
        try:
            # Read and parse source file
            source = Path(source_path).read_text()
            lexer = Lexer(source, source_path)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            module = parser.parse_module()

            # Collect test functions
            tests = get_test_functions(module)
            all_test_fns.extend(tests)

        except Exception as e:
            print(f"Error scanning {source_path}: {e}", file=sys.stderr)
            return False

    if not all_test_fns:
        print("Warning: No @test functions found", file=sys.stderr)

    # Generate test main source
    test_main_source = generate_test_main_source(all_test_fns)
    Path(output_path).write_text(test_main_source)
    print(f"Generated test main with {len(all_test_fns)} tests -> {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='ritz0 - The Ritz Bootstrap Compiler',
        epilog='Compilation model: one .ritz file → one .ll file. Imports become external declarations.'
    )
    parser.add_argument('source', nargs='*', help='Source file(s) to compile')
    parser.add_argument('-o', '--output', help='Output file (.ll) - required for compile mode')
    parser.add_argument('--test', action='store_true', help='Run tests for specified file')
    parser.add_argument('--test-all', action='store_true', help='Discover and run all tests in test/ directory')
    parser.add_argument('--emit-test-main', action='store_true',
                        help='Generate test main source that runs all @test functions')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-runtime', action='store_true', help='Do not emit _start entry point (for libraries)')
    parser.add_argument('--check-names', action='store_true',
                        help='Verify all referenced names are defined before IR emission')
    parser.add_argument('--no-check-ownership', action='store_true',
                        help='Disable ownership/borrowing checks (enabled by default)')
    parser.add_argument('--check-types', action='store_true',
                        help='Enable type checking (catches type errors before IR generation)')
    parser.add_argument('--deps',
                        help='JSON dependency specification for RFC #109 namespacing')
    parser.add_argument('--sources',
                        help='JSON list of source directories to search for imports (e.g., ["src", "kernel/src"])')
    parser.add_argument('--project-root',
                        help='Explicit project root for import resolution (source roots are relative to this)')
    parser.add_argument('--target', default='x86_64-unknown-linux-gnu',
                        help='Target triple (default: x86_64-unknown-linux-gnu). '
                             'Use x86_64-none-elf for freestanding/kernel builds.')
    parser.add_argument('--target-os', default='linux',
                        help='Target OS for conditional compilation (default: linux). '
                             'Used with [[target_os = "..."]] attributes.')

    args = parser.parse_args()

    # Emit test main mode - generates a test harness source file
    if args.emit_test_main:
        if not args.source:
            print("Error: --emit-test-main requires source file(s)", file=sys.stderr)
            sys.exit(1)
        if not args.output:
            print("Error: --emit-test-main requires -o/--output", file=sys.stderr)
            sys.exit(1)
        success = emit_test_main(args.source, args.output)
        sys.exit(0 if success else 1)

    # Test mode
    if args.test or args.test_all:
        from test_runner import run_test_file

        # Determine which test files to run
        if args.test_all:
            test_files = discover_tests()
            if not test_files:
                print("Error: no test files found in test/ directory", file=sys.stderr)
                sys.exit(1)
        elif args.source:
            test_files = args.source  # Now a list
        else:
            print("Error: --test requires a source file, or use --test-all", file=sys.stderr)
            sys.exit(1)

        total_passed = 0
        total_failed = 0
        all_failures = []

        for file_path in test_files:
            if args.verbose:
                print(f"\n{file_path}:")

            try:
                passed, failed, failures = run_test_file(file_path, args.verbose)
                total_passed += passed
                total_failed += failed
                all_failures.extend(failures)
            except Exception as e:
                print(f"Error in {file_path}: {e}", file=sys.stderr)
                total_failed += 1
                all_failures.append(f"{file_path}: error")

        # Summary
        print(f"\n{total_passed} passed, {total_failed} failed")

        if all_failures:
            print("\nFailures:")
            for f in all_failures:
                print(f"  - {f}")

        sys.exit(0 if total_failed == 0 else 1)

    # Compile mode
    else:
        if not args.source:
            print("Error: source file required", file=sys.stderr)
            parser.print_help()
            sys.exit(1)

        if len(args.source) > 1:
            print("Error: compile mode only accepts one source file", file=sys.stderr)
            sys.exit(1)

        if not args.output:
            print("Error: -o/--output required", file=sys.stderr)
            sys.exit(1)

        # Parse dependencies if provided
        dependencies = None
        if args.deps:
            import json
            from import_resolver import DependencyMapping
            deps_data = json.loads(args.deps)
            dependencies = {}
            for name, spec in deps_data.items():
                dependencies[name] = DependencyMapping(
                    name=name,
                    path=Path(spec["path"]),
                    sources=spec["sources"]
                )

        # Parse source roots if provided
        source_roots = None
        if args.sources:
            import json
            source_roots = json.loads(args.sources)

        # Get project root if provided
        project_root = args.project_root

        success = compile_file(args.source[0], args.output,
                               no_runtime=args.no_runtime,
                               check_names=args.check_names,
                               check_ownership=not args.no_check_ownership,
                               check_types=args.check_types,
                               dependencies=dependencies,
                               source_roots=source_roots,
                               project_root=project_root,
                               target=args.target,
                               target_os=args.target_os)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
