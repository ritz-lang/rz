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

import os
import sys
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from lexer import Lexer, LexerError
from parser import Parser, ParseError
from enum_from import rewrite_enum_from
from emitter_llvmlite import emit as emit_llvmlite, EmitError
from import_resolver import ImportResolver, ImportError as RitzImportError
from selective_import import check_selective_imports
from import_visibility import check_import_visibility
import module_interface
import main_abi
from name_resolver import resolve_names, NameError as RitzNameError
from binder_names import check_binders
from builtin_types import check_builtin_impls, check_unknown_impl_targets
from impl_placement import check_impl_placement
from type_names import check_unknown_type_names
from reachability import check_reachable
from no_effect import check_no_effect
from move_checker import MoveChecker, OwnershipError
from monomorph import infer_struct_lit_args
from type_checker import TypeError as RitzTypeError
from typed import type_module
from const_eval import evaluate_array_sizes, ConstEvalError
from emitter.fn_cache import (
    source_file_hash, hash_maps,
    read_current_sig, write_sig_file, check_source_hash,
    check_import_hashes, check_import_misses, build_import_hashes,
    build_sig_data, detect_sig_changes, invalidate_dependents,
    compile_mode_key, check_output_entry, build_outputs,
)
import ritz_ast as rast


def _compile_mode(no_runtime, check_names, check_ownership, check_types,
                  dependencies, source_roots, project_root, target, target_os,
                  test_mode, stack_protector=False) -> dict:
    """Every compile_file input, besides the sources themselves, that shapes
    the output or whether the compile succeeds (AGAST #2020).

    The source-level fast path may only reuse an output built under the same
    mode.  Covered: the emit flags (no_runtime, test_mode, target, target_os,
    stack_protector);
    the import roots, which decide WHICH file an import resolves to (the
    import hashes only vouch for the files the last compile resolved), as
    ImportResolver resolves them; and the checks, since a skip would stand in
    for a check the earlier compile never ran.  Paths are resolved so the same
    roots spelled differently are one mode.
    """
    root = Path(project_root).resolve() if project_root else None
    roots = []
    for sr in source_roots or []:
        p = Path(sr)
        if not p.is_absolute() and root is not None:
            p = root / p
        roots.append(str(p.resolve()))
    ritz_path = [str(Path(p).resolve())
                 for p in os.environ.get('RITZ_PATH', '').split(':') if p]
    deps = {name: [str(Path(d.path).resolve()), list(d.sources)]
            for name, d in (dependencies or {}).items()}
    return {
        'no_runtime': bool(no_runtime),
        'test_mode': bool(test_mode),
        'target': target,
        'target_os': target_os,
        'stack_protector': bool(stack_protector),
        'check_names': bool(check_names),
        'check_ownership': bool(check_ownership),
        'check_types': bool(check_types),
        'project_root': str(root) if root else None,
        'source_roots': roots,
        'ritz_path': ritz_path,
        'dependencies': deps,
        'interfaces': module_interface.enabled(),
    }


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


@dataclass
class _Compile:
    """One compile_file call: its inputs, and what each pass leaves for the
    passes after it.  A pass is a function over this, run in PASSES order; it
    returns False after printing why the compile fails, else True."""
    source_path: str
    output_path: str
    no_runtime: bool = False
    check_names: bool = False
    check_ownership: bool = False
    check_types: bool = False
    dependencies: Optional[dict] = None
    source_roots: Optional[list] = None
    project_root: Optional[str] = None
    target: str = 'x86_64-unknown-linux-gnu'
    target_os: str = 'linux'
    test_mode: bool = False
    stack_protector: bool = False
    # Set up by compile_file before the passes run.
    source: str = ''
    source_abs_path: str = ''
    mode_key: str = ''
    # _parse
    module: Optional[rast.Module] = None
    source_hashes: Optional[tuple] = None
    original_import_paths: List[str] = field(default_factory=list)
    # _lower_main: this file's main took the entry adapter
    main_lowered: bool = False
    # _resolve
    module_names: Set[str] = field(default_factory=set)
    import_hashes: dict = field(default_factory=dict)
    import_misses: List[str] = field(default_factory=list)


def _report(errors, prefix: str = '') -> bool:
    """Print each error to stderr, after `prefix`; True if there were none."""
    for err in errors:
        print(f"{prefix}{err}", file=sys.stderr)
    return not errors


def _up_to_date(ctx: _Compile) -> bool:
    """The source-file-level fast path: may this compile be skipped?

    Only if the .ll output exists, is newer than the source, the source hash
    matches the cached hash in .ritz.sig, AND every transitive import
    still hashes as recorded. The import check matters:
    the .ll bakes in imported struct layouts (field offsets), constants
    and signatures, so an unchanged module over a changed import is
    still stale (AGAST #1674). The sig must also vouch for THIS output
    in THIS mode: it is keyed by source alone, so another flag set or
    another output path must not count as "unchanged" (AGAST #2020).
    And every candidate import resolution probed and missed must still
    be missing: a new file there would change what an import resolves
    to, behind import hashes that all still match (AGAST #2030).
    And the sig must come from THIS ritz0: read_current_sig drops one
    another ritz0 wrote, so editing ritz0 recompiles (AGAST #3086).
    """
    output_file = Path(ctx.output_path)
    if not output_file.exists():
        return False
    source_mtime = Path(ctx.source_path).stat().st_mtime
    output_mtime = output_file.stat().st_mtime
    prior_sig = read_current_sig(ctx.source_abs_path)
    return (output_mtime >= source_mtime
            and check_source_hash(ctx.source, ctx.source_abs_path)
            and check_import_hashes(prior_sig)
            and check_import_misses(prior_sig)
            and check_output_entry(prior_sig, ctx.output_path, ctx.mode_key))


def _parse(ctx: _Compile) -> bool:
    """Lex and parse (counted: RITZ0_PARSE_LOG, module_interface.PARSED)."""
    tokens, module = module_interface.parse_source_tokens(ctx.source, ctx.source_path)

    # The fn cache's token hashes, from this one lex and parse (AGAST
    # #2807: it used to lex the source four more times). Now, while
    # `module.items` are still this file's: _resolve replaces them.
    try:
        ctx.source_hashes = hash_maps(tokens, module.items)
    except Exception:
        ctx.source_hashes = None
    del tokens

    # Capture import paths BEFORE _resolve — that pass replaces
    # `module.items` with merged items from all transitive imports and
    # strips the original Import nodes.  Without this snapshot, the
    # `import_paths` written by _emit would be an empty list,
    # which causes every `.ritz.sig` to be written with `imports: []`,
    # which causes `invalidate_dependents` to never propagate signature
    # changes to importers — the per-function caching layer silently
    # never invalidates anyone, manifesting as "I edited a lib and the
    # binary still has stale code" until you `rm -rf .ritz-cache`.
    ctx.original_import_paths = [
        '.'.join(item.path) for item in module.items if isinstance(item, rast.Import)]
    ctx.module = module
    return True


def _lower_main(ctx: _Compile) -> bool:
    """The entry ABI (main_abi.py, AGAST #200): refuse a `main` of no
    accepted shape; give a Ritz-native one its C-entry adapter. Before
    _resolve, so the adapter is checked and emitted like any fn. Not in
    test mode: the runner supplies `main` and the file's own is dropped."""
    if ctx.test_mode:
        return True
    before = main_abi.find_main(ctx.module)
    if not _report(main_abi.lower_main(ctx.module, ctx.source_path)):
        return False
    ctx.main_lowered = before is not None and before.name != "main"
    return True


def _resolve(ctx: _Compile) -> bool:
    """Resolve imports and merge them into one module. Imported modules
    come from their interfaces (G9, AGAST #1810: module_interface.py),
    so only this file is parsed; only its bodies are emitted anyway.
    use_cache=False: the older .ritz-meta stubs lose generic bodies."""
    resolver = ImportResolver(
        ctx.project_root, use_cache=False, dependencies=ctx.dependencies,
        source_roots=ctx.source_roots, use_interfaces=module_interface.enabled())
    imports = [item for item in ctx.module.items if isinstance(item, rast.Import)]
    module = resolver.resolve(ctx.module, ctx.source_path)
    # R54: each name in `import m { … }` is one m defines (AGAST #3466).
    if not _report(check_selective_imports(
            imports, resolver, ctx.source_abs_path), "Error: "):
        return False
    # A plain `import` is private: what reaches this file only through
    # another module's plain import is undefined here (AGAST #3891).
    if not _report(check_import_visibility(
            ctx.module.items, resolver, ctx.source_abs_path, module),
            "Error: "):
        return False

    # What `token.Kind` may be qualified by: every module this compile saw.
    ctx.module_names = {Path(f).stem for f in resolver.processed_files}
    for aliases in resolver.import_aliases.values():
        ctx.module_names.update(aliases)

    # Hash every transitive import now, before emission, so the sig vouches
    # for the sources this .ll was actually built from (AGAST #1674).
    # The ritz.toml files that registered an imported namespace count too:
    # their `sources` decide what `<name>.*` resolves to (AGAST #2087).
    ctx.import_hashes = build_import_hashes(
        [f for f in resolver.processed_files if f != ctx.source_abs_path]
        + sorted(resolver.config_files))
    # ...and the candidates it probed and missed on the way (AGAST #2030).
    ctx.import_misses = sorted(resolver.missed_candidates)

    # Filter out items that don't match target_os
    # This must happen after import resolution but before name resolution
    # so that name resolution doesn't see excluded items
    ctx.module = resolver.resolve_struct_variants(
        _filter_by_target_os(module, ctx.target_os))
    return True


def _check_impl_targets(ctx: _Compile) -> bool:
    """An `impl` on a built-in type (Span, StrView, Option, Result) no
    module declares (AGAST #3162).  After the merge, so an imported
    `struct Span<T>` makes Span an ordinary struct.  ...and on a type
    nothing declares or imports (AGAST #3264).  ...and one outside its
    type's (or trait's) file, or on one instantiation (LARB R65, #3493)."""
    errors = check_builtin_impls(ctx.module)
    errors += check_unknown_impl_targets(ctx.module)
    errors += check_impl_placement(ctx.module)
    return _report(errors, "Error: ")


def _rewrite_enum_from(ctx: _Compile) -> bool:
    """`E.from(v)` -> the generated `E__from(v)` (LANGUAGE_SPEC §10.4)."""
    return _report(rewrite_enum_from(ctx.module), "Error: ")


def _eval_array_sizes(ctx: _Compile) -> bool:
    """Evaluate constant expressions in array sizes.  This must happen
    before name resolution since it transforms the AST."""
    return _report(evaluate_array_sizes(ctx.module), "Const eval error: ")


def _check_type_names(ctx: _Compile) -> bool:
    """A written type name nothing declares or imports (AGAST #3932): after
    the merge, so an import counts, and after _check_impl_targets, which
    judges an impl's target."""
    return _report(check_unknown_type_names(ctx.module, ctx.module_names), "Error: ")


def _check_binders(ctx: _Compile) -> bool:
    """A local named like a const, global or variant (AGAST #2407). Before
    monomorphisation, so a generic fn is judged whether or not it's used."""
    return _report(check_binders(ctx.module, ctx.source_abs_path), "Name error: ")


def _check_reachable(ctx: _Compile) -> bool:
    """A statement that can never run (AGAST #2520, LARB): before
    monomorphisation, so a generic fn is judged whether or not it's used."""
    return _report(check_reachable(ctx.module, ctx.source_abs_path))


def _check_no_effect(ctx: _Compile) -> bool:
    """A statement with no effect (LARB R64, AGAST #3491). After _type: a
    discarded expression the typing pass already refused (a whole array
    alone, #3189) keeps that error, which the emitter reports. Still before
    monomorphisation, so a generic fn is judged whether or not it's used."""
    return _report(check_no_effect(ctx.module, ctx.source_abs_path,
                                   ctx.module.typed))


def _check_names(ctx: _Compile) -> bool:
    """`--check-names`: every referenced name is defined."""
    if not ctx.check_names:
        return True
    return _report(resolve_names(ctx.module, ctx.module_names), "Name error: ")


def _infer_struct_lit_args(ctx: _Compile) -> bool:
    """A generic struct literal's left-out type args (§9.2, AGAST #3407):
    before the checkers, so the move checker sees `Box2 { v: d }` as
    the Box2<D> it is.  The rest of monomorphisation runs in _emit."""
    infer_struct_lit_args(ctx.module)
    return True


def _type(ctx: _Compile) -> bool:
    """The typing pass (typed.py, AGAST #3448): type every expression into
    `module.typed`, which the passes after it read.  Always runs; its errors
    are _check_types' and _check_ownership's to report."""
    type_module(ctx.module, ctx.module_names)
    return True


def _check_types(ctx: _Compile) -> bool:
    """`--check-types`: report the typing pass's type errors."""
    if not ctx.check_types:
        return True
    return _report(ctx.module.typed.errors, "Type error: ")


def _check_ownership(ctx: _Compile) -> bool:
    """Move and borrow rules (on unless --no-check-ownership)."""
    if not ctx.check_ownership:
        return True
    ownership_errors = MoveChecker().check(ctx.module)
    if not ownership_errors:
        return True
    # `c` in a reference slot wants `@c`, not "cannot move out".
    slot_errors = ctx.module.typed.slot_errors
    explains = [err for err in slot_errors if not err.after_moves]
    if not _report(explains, "Type error: "):
        return False
    _report(ownership_errors, "Ownership error: ")
    # The rest after it, as ritz1 prints them (#3189).
    _report(slot_errors, "Type error: ")
    return False


def _fn_cache(ctx: _Compile) -> tuple:
    """Per-fn cache state for _emit: (fn_cache_data, fn_hashes, sig_hashes,
    old_sig_data).  Detects signature changes and invalidates the modules
    that depend on them, before emission."""
    try:
        if ctx.source_hashes is None:
            raise ValueError("fn hashes unavailable")
        fn_hashes, sig_hashes = ctx.source_hashes
        # Another ritz0's sig carries no outputs or fn IR forward (#3086).
        old_sig_data = read_current_sig(ctx.source_abs_path)

        # Detect signature changes and invalidate dependent modules
        changed_sigs = detect_sig_changes(ctx.source_abs_path, sig_hashes)
        if changed_sigs:
            _invalidate_dependents(ctx, changed_sigs)

        # Per-fn IR reuse is OFF: every fn is emitted fresh (AGAST #2019).
        #
        # The only "hits" the emitter ever honoured were fns the async
        # transform synthesizes: an `async fn f` yields a constructor
        # also named `f`, with no `source_file`, so `_should_emit_body`
        # consulted the cache for it (source fns carry `source_file` and
        # are always emitted).  Its body was skipped, `_splice_cached_ir`
        # failed to match the `... "no-builtins"` declare, and a warm
        # recompile shipped `f_poll` with `f` only declared — a link
        # failure that build.py's shared CAS then kept for every worktree.
        # Splicing can't be byte-identical to a cold compile in any case:
        # a cached block's `!dbg !N` ids belong to the compile that wrote
        # it.  The sig is still written (source-hash fast path, sig-change
        # invalidation); its stored IR is just never spliced back in.
        fn_cache_data = {
            'cache_hits': {},
            'cache_misses': dict(fn_hashes),
            'sig_data': old_sig_data,
        }
        return fn_cache_data, fn_hashes, sig_hashes, old_sig_data
    except Exception:
        return None, {}, {}, None


def _invalidate_dependents(ctx: _Compile, changed_sigs) -> None:
    """Invalidate the modules under this source's project root (the nearest
    ancestor with `.git` or `ritzlib/`) that import a changed signature."""
    project_root = str(Path(ctx.source_path).resolve().parent)
    for parent in Path(ctx.source_path).resolve().parents:
        if (parent / '.git').exists() or (parent / 'ritzlib').is_dir():
            project_root = str(parent)
            break
    invalidate_dependents(ctx.source_abs_path, changed_sigs, project_root)


def _emit(ctx: _Compile) -> bool:
    """Monomorphise and emit IR (emitter_llvmlite.emit), write the .ll, then
    the .ritz.sig cache.

    Always separate compilation: each source file -> one .ll file.
    Functions from the current file: define (full body).  Functions from
    imports: declare (external reference).  --no-runtime only controls
    whether to emit the _start entry point.
    """
    fn_cache_data, fn_hashes, sig_hashes, old_sig_data = _fn_cache(ctx)
    source_path_obj = Path(ctx.source_path)
    source_dir = str(source_path_obj.parent.resolve()) if source_path_obj.parent else "."
    emit_result = emit_llvmlite(
        ctx.module, no_runtime=ctx.no_runtime,
        source_file=source_path_obj.name, source_dir=source_dir,
        main_source_path=ctx.source_abs_path,
        target=ctx.target, target_os=ctx.target_os, test_mode=ctx.test_mode,
        stack_protector=ctx.stack_protector,
        # Per-fn IR reuse is keyed on the source alone, so it cannot tell a
        # test-mode compile (no `main`) from a normal one: test mode always
        # emits fresh.
        # The adapter's `main` is not the source's: no per-fn reuse either.
        fn_cache_data=None if ctx.test_mode or ctx.main_lowered else fn_cache_data,
        module_names=ctx.module_names)

    if fn_cache_data is not None and isinstance(emit_result, tuple):
        ir, emitted_fn_ir = emit_result
    else:
        ir = emit_result
        emitted_fn_ir = {}

    Path(ctx.output_path).write_text(ir)

    # --- Write .ritz.sig cache with emitted function IR ---
    try:
        # The import paths _parse captured: the resolved module no longer
        # contains Import nodes (they're replaced by the merged imported items).
        sig_data = build_sig_data(
            source=ctx.source,
            fn_hashes=fn_hashes,
            sig_hashes=sig_hashes,
            fn_ir=emitted_fn_ir,
            imports=ctx.original_import_paths,
            old_sig_data=old_sig_data,
            import_hashes=ctx.import_hashes,
            import_misses=ctx.import_misses,
            outputs=build_outputs(
                old_sig_data, ctx.source, ctx.import_hashes, ctx.output_path,
                ctx.mode_key, ir, import_misses=ctx.import_misses),
        )
        write_sig_file(ctx.source_abs_path, sig_data)
    except Exception as e:
        # Cache write failure is non-fatal
        print(f"Warning: cache write failed: {e}", file=sys.stderr)
    return True


# The compile, in order: parse -> resolve -> check[] -> monomorph -> emit
# (LARB review/5 N2, AGAST #3449).  The order is load-bearing: the lowering
# passes (_rewrite_enum_from, _eval_array_sizes) run between the first checks,
# and _infer_struct_lit_args, monomorph's first step, runs before the typing
# pass (_type) the type and ownership checks read; the rest of monomorphisation, and the checks that
# judge each generic instance, still run inside emitter_llvmlite.emit.
PASSES = (
    _parse,
    _lower_main,
    _resolve,
    _check_impl_targets,
    _rewrite_enum_from,
    _eval_array_sizes,
    _check_type_names,
    _check_binders,
    _check_reachable,
    _check_names,
    _infer_struct_lit_args,
    _type,
    _check_types,
    _check_no_effect,
    _check_ownership,
    _emit,
)


def compile_file(source_path: str, output_path: str, no_runtime: bool = False,
                  check_names: bool = False, check_ownership: bool = False,
                  check_types: bool = False, dependencies: dict = None,
                  source_roots: list = None, project_root: str = None,
                  target: str = 'x86_64-unknown-linux-gnu',
                  target_os: str = 'linux', test_mode: bool = False,
                  stack_protector: bool = False) -> bool:
    """Compile a single Ritz source file to LLVM IR, by running PASSES.

    Each .ritz file compiles to one .ll file; imports are resolved and
    emitted as external declarations for linking.  The arguments are
    _Compile's inputs; see ritz0.py's argument parser for each flag.
    `test_mode` compiles the root of a test binary (LANGUAGE_SPEC §17.1).
    """
    try:
        ctx = _Compile(source_path, output_path, no_runtime, check_names,
                       check_ownership, check_types, dependencies, source_roots,
                       project_root, target, target_os, test_mode,
                       stack_protector)
        ctx.source = Path(source_path).read_text()
        ctx.source_abs_path = str(Path(source_path).resolve())
        ctx.mode_key = compile_mode_key(_compile_mode(
            no_runtime, check_names, check_ownership, check_types,
            dependencies, source_roots, project_root, target, target_os,
            test_mode, stack_protector))
        if _up_to_date(ctx):
            print(f"Skipped {source_path} (unchanged)")
            return True
        for compile_pass in PASSES:
            if not compile_pass(ctx):
                return False
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
    parser.add_argument('--stack-protector', action='store_true',
                        help='Give every defined function except a [[naked]] one '
                             'LLVM\'s sspstrong (AGAST #2590). The program must '
                             'define __stack_chk_guard and __stack_chk_fail.')

    args = parser.parse_args()

    if args.test or args.test_all:
        from test_runner import run_files, install_signal_handlers

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

        # Shared with build.py's in-process test unit (AGAST #1915).
        sys.exit(run_files(test_files, args.verbose, args.compiler))

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
                               test_mode=args.test_table,
                               stack_protector=args.stack_protector)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
