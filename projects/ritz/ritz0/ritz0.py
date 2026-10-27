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
from typing import List

from lexer import Lexer, LexerError
# Use generated parser with adapter (comment out to use hand-written parser)
# from parser_adapter import Parser, ParseError  # Generated parser
from parser import Parser, ParseError  # Hand-written parser
from emitter_llvmlite import emit as emit_llvmlite, EmitError
from import_resolver import ImportResolver, ImportError as RitzImportError
import module_interface
from name_resolver import resolve_names, NameError as RitzNameError
from move_checker import MoveChecker, OwnershipError
from type_checker import TypeChecker, TypeError as RitzTypeError
from const_eval import evaluate_array_sizes, ConstEvalError
from emitter.fn_cache import (
    source_file_hash, build_hash_map, build_sig_hash_map,
    read_sig_file, write_sig_file, check_cache, check_source_hash,
    check_import_hashes, build_import_hashes,
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
                  target_os: str = 'linux', test_mode: bool = False) -> bool:
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
        test_mode: Compile as the root of a test binary (LANGUAGE_SPEC §17.1):
                   emit the `[[test]]` table and a `_start` that calls the
                   ritzunit runner's `main`; drop the file's own `main`.
    """
    try:
        # Read source file
        source = Path(source_path).read_text()

        # Get absolute path for source file tracking
        source_abs_path = str(Path(source_path).resolve())

        # --- Incremental compilation: source-file-level hash check ---
        # If the .ll output exists, is newer than the source, the source hash
        # matches the cached hash in .ritz.sig, AND every transitive import
        # still hashes as recorded, skip everything. The import check matters:
        # the .ll bakes in imported struct layouts (field offsets), constants
        # and signatures, so an unchanged module over a changed import is
        # still stale (AGAST #1674).
        output_file = Path(output_path)
        if output_file.exists():
            source_mtime = Path(source_path).stat().st_mtime
            output_mtime = output_file.stat().st_mtime
            if (output_mtime >= source_mtime
                    and check_source_hash(source, source_abs_path)
                    and check_import_hashes(read_sig_file(source_abs_path))):
                print(f"Skipped {source_path} (unchanged)")
                return True

        # Extract directory and filename for debug info
        source_path_obj = Path(source_path)
        source_file = source_path_obj.name
        source_dir = str(source_path_obj.parent.resolve()) if source_path_obj.parent else "."

        # Lex and parse (counted: RITZ0_PARSE_LOG, module_interface.PARSED)
        module = module_interface.parse_source(source, source_path)

        # Capture import paths BEFORE resolve_imports — that pass replaces
        # `module.items` with merged items from all transitive imports and
        # strips the original Import nodes.  Without this snapshot, the
        # `import_paths` extraction below the emit step sees an empty list,
        # which causes every `.ritz.sig` to be written with `imports: []`,
        # which causes `invalidate_dependents` to never propagate signature
        # changes to importers — the per-function caching layer silently
        # never invalidates anyone, manifesting as "I edited a lib and the
        # binary still has stale code" until you `rm -rf .ritz-cache`.
        original_import_paths: List[str] = []
        for _item in module.items:
            if isinstance(_item, rast.Import):
                original_import_paths.append('.'.join(_item.path))

        # Resolve imports and merge them into one module. Imported modules
        # come from their interfaces (G9, AGAST #1810: module_interface.py),
        # so only this file is parsed; only its bodies are emitted anyway.
        # use_cache=False: the older .ritz-meta stubs lose generic bodies.
        resolver = ImportResolver(project_root, use_cache=False, dependencies=dependencies,
                                  source_roots=source_roots,
                                  use_interfaces=module_interface.enabled())
        module = resolver.resolve(module, source_path)

        # Hash every transitive import now, before emission, so the sig vouches
        # for the sources this .ll was actually built from (AGAST #1674).
        import_hashes = build_import_hashes(
            f for f in resolver.processed_files if f != source_abs_path)

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
                           test_mode=test_mode,
                           # Per-fn IR reuse is keyed on the source alone, so
                           # it cannot tell a test-mode compile (no `main`)
                           # from a normal one: test mode always emits fresh.
                           fn_cache_data=None if test_mode else fn_cache_data)

        if fn_cache_data is not None and isinstance(emit_result, tuple):
            ir, emitted_fn_ir = emit_result
        else:
            ir = emit_result
            emitted_fn_ir = {}

        # Write output
        Path(output_path).write_text(ir)

        # --- Write .ritz.sig cache with emitted function IR ---
        try:
            # Use the import paths captured BEFORE resolve_imports — the
            # post-resolved module no longer contains Import nodes (they're
            # replaced by the merged imported items).
            sig_data = build_sig_data(
                source=source,
                fn_hashes=fn_hashes,
                sig_hashes=sig_hashes,
                fn_ir=emitted_fn_ir,
                imports=original_import_paths,
                old_sig_data=old_sig_data,
                import_hashes=import_hashes,
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
    except EmitError as e:
        # A source error the emitter is the first pass to notice. It already
        # carries `file:line:column`, so report it like any other diagnostic
        # and stop -- re-raising would bury it under a Python traceback.
        print(f"Compiler error: {e}", file=sys.stderr)
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


def _log_launch() -> None:
    """Append one line per ritz0 process to $RITZ_TEST_RITZ0_LOG, if set.

    AGAST #1805: lets the pytest suite count how many times it pays ritz0's
    start-up cost (import of the emitter + llvmlite) — see
    ritz0_inproc.py.  A run forked by ritz0_inproc (no interpreter start-up)
    is tagged `inproc `, so the log tells the two apart.
    """
    import os
    log = os.environ.get("RITZ_TEST_RITZ0_LOG")
    if log:
        tag = "inproc " if os.environ.get("RITZ_TEST_RITZ0_INPROC") else ""
        with open(log, "a") as f:
            f.write(f"{tag}{os.getpid()} {' '.join(sys.argv[1:])}\n")


def main():
    _log_launch()
    parser = argparse.ArgumentParser(
        description='ritz0 - The Ritz Bootstrap Compiler',
        epilog='Compilation model: one .ritz file → one .ll file. Imports become external declarations.'
    )
    parser.add_argument('source', nargs='*', help='Source file(s) to compile')
    parser.add_argument('-o', '--output', help='Output file (.ll) - required for compile mode')
    parser.add_argument('--test', action='store_true', help='Run tests for specified file')
    parser.add_argument('--test-all', action='store_true', help='Discover and run all tests in test/ directory')
    parser.add_argument('--compiler', default='ritz0',
                        choices=('ritz0', 'ritz1', 'ritz1_selfhosted'),
                        help='With --test: the compiler that builds each test binary, '
                             'ritzunit included (default: ritz0)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-runtime', action='store_true', help='Do not emit _start entry point (for libraries)')
    parser.add_argument('--test-table', action='store_true',
                        help='Compile as a test binary root: emit the [[test]] table for the '
                             'ritzunit runner (LANGUAGE_SPEC §17.1)')
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

    if args.test or args.test_all:
        from test_runner import run_test_file, install_signal_handlers

        # AGAST #1392: this is the entry point build.py drives, and the one
        # that was being killed by an outer `timeout`. Without a handler the
        # scratch-dir `finally` never ran and the leaked `ritzlib` symlink
        # formed a collection-wedging cycle.
        install_signal_handlers()

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
                passed, failed, failures = run_test_file(file_path, args.verbose,
                                                         args.compiler)
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
                               target_os=args.target_os,
                               test_mode=args.test_table)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
