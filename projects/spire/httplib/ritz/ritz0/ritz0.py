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

from lexer import Lexer, LexerError, set_reritz_mode, RERITZ_MODE
# Use generated parser with adapter (comment out to use hand-written parser)
# from parser_adapter import Parser, ParseError  # Generated parser
from parser import Parser, ParseError  # Hand-written parser
from emitter_llvmlite import emit as emit_llvmlite, get_test_functions, generate_test_main_source
from import_resolver import resolve_imports, ImportError as RitzImportError
from name_resolver import resolve_names, NameError as RitzNameError
from move_checker import MoveChecker, OwnershipError
from type_checker import TypeChecker, TypeError as RitzTypeError
from const_eval import evaluate_array_sizes, ConstEvalError


def compile_file(source_path: str, output_path: str, no_runtime: bool = False,
                  check_names: bool = False, check_ownership: bool = False,
                  check_types: bool = False, dependencies: dict = None) -> bool:
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
    """
    try:
        # Read source file
        source = Path(source_path).read_text()

        # Get absolute path for source file tracking
        source_abs_path = str(Path(source_path).resolve())

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
        module = resolve_imports(module, source_path, use_cache=False, dependencies=dependencies)

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

        # Emit IR
        # Always use separate compilation: each source file → one .ll file
        # Functions from current file: define (full body)
        # Functions from imports: declare (external reference)
        # --no-runtime only controls whether to emit _start entry point
        ir = emit_llvmlite(module, no_runtime=no_runtime,
                           source_file=source_file, source_dir=source_dir,
                           main_source_path=source_abs_path)

        # Write output
        Path(output_path).write_text(ir)

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
    parser.add_argument('--syntax', choices=['legacy', 'reritz'], default=None,
                        help='Syntax mode: legacy (current) or reritz (new RERITZ syntax). '
                             'Can also be set via RITZ_SYNTAX environment variable.')

    args = parser.parse_args()

    # Set syntax mode if specified
    if args.syntax:
        set_reritz_mode(args.syntax == 'reritz')

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

        success = compile_file(args.source[0], args.output,
                               no_runtime=args.no_runtime,
                               check_names=args.check_names,
                               check_ownership=not args.no_check_ownership,
                               check_types=args.check_types,
                               dependencies=dependencies)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
