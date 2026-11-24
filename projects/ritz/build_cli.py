"""build.py's command line: the `cmd_*` handlers and `main`.

Split out of build.py (AGAST #3632), which still runs it: `python3 build.py
build <pkg>` is the entry point `rz`, the Makefile and the docs use.
"""

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Optional

import bounded_run
import manifest
from build_pipeline import (EXIT_SETUP, RITZ0, ROOT, build_package, compile_binary,
                            get_build_cache, get_output_dir, invoked_package_path)
from build_testrun import run_test_sh, run_tests, test_run_dir, unit_file, unit_plan
from manifest import (StrayTestsDirError, find_all_packages, find_package_at, find_package_by_name_or_path,
                      find_packages, get_build_profile, plan_binaries)


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
    # The logical path, for the per-root output dir (#3818). --all globs
    # under the cwd, so its package paths are already unresolved.
    invoked_as = None if args.all else invoked_package_path(args.name)
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

        result = build_package(pkg_dir, config, keep_artifacts=keep_artifacts, use_cache=use_cache, profile_name=profile_name, compiler=compiler,
                               invoked_as=invoked_as if invoked_as else pkg_dir)
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

    # As cmd_build (#3818): a package reached through another tree's
    # symlink builds into a per-root dir, and its tests run in a per-root
    # shadow of the package, test_run_dir (AGAST #3831). --all globs under
    # the cwd, so its package paths are already unresolved.
    invoked_as = None if args.all else invoked_package_path(args.name)

    def run_dir(pkg_dir: Path, config: dict, invoked: Optional[Path]) -> Path:
        out_dir = get_output_dir(pkg_dir, get_build_profile(config, profile_name),
                                 invoked_as=invoked)
        return test_run_dir(pkg_dir, config, out_dir)

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
                             profile_name=profile_name, compiler=compiler,
                             invoked_as=invoked_as)
        # Same package path as the --unit-plan that built it, so the same
        # run dir; recomputed rather than read from the plan.
        if unit == "file":
            return unit_file(run_dir(pkg_dir, config, invoked_as), Path(args.unit_file),
                             Path(args.unit_result), compiler, use_cache=use_cache)
        return 0 if run_test_sh(run_dir(pkg_dir, config, invoked_as)) else 1

    all_passed = True
    for pkg_dir, config in targets:
        invoked = invoked_as if invoked_as else pkg_dir
        # Check if this is a test-only package
        is_test_only = config.get("build", {}).get("test_only", False)

        if is_test_only:
            # For test-only packages, run tests directly without building a binary
            print(f"📦 {config['package']['name']} (test-only)")
            if not run_tests(pkg_dir, config, compiler,
                             run_dir=run_dir(pkg_dir, config, invoked), use_cache=use_cache):
                all_passed = False
        else:
            # Normal package: build then test
            result = build_package(pkg_dir, config, keep_artifacts=keep_artifacts, use_cache=use_cache, profile_name=profile_name, compiler=compiler,
                                   invoked_as=invoked)

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
            elif not run_tests(pkg_dir, config, compiler,
                               run_dir=run_dir(pkg_dir, config, invoked), use_cache=use_cache):
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
    result = bounded_run.child(
        [sys.executable, str(RITZ0), "--test-all", "-v"],
        cwd=ritz0_dir
    )
    return result.returncode


def run_output_dir(src_path: Path) -> Path:
    """Where `build.py run` links `src_path`: `build/run/<digest>/` (AGAST #2252).

    The digest is of the source's resolved path, so each file gets its own
    directory however it was spelled on the command line, and two sources with
    the same stem (every `<dir>/main.ritz`) no longer share one binary and
    manifest. Linking to `build/<stem>` made each run relink over the last one,
    and two runs at once raced on the file (#2251).
    """
    digest = hashlib.sha256(str(src_path.resolve()).encode()).hexdigest()[:16]
    return ROOT / "build" / "run" / digest


def cmd_run(args):
    """Compile and run a single .ritz file."""
    src_path = Path(args.file)
    if not src_path.exists():
        print(f"File not found: {src_path}", file=sys.stderr)
        return 1

    keep_artifacts = getattr(args, 'debug', False)
    name = src_path.stem

    # Each source gets its own directory, so same-stem sources don't share a binary.
    out_dir = run_output_dir(src_path)
    out_dir.mkdir(parents=True, exist_ok=True)

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
    result = bounded_run.user_program([str(bin_path)] + args.args)
    return result.returncode


def cmd_clean(args):
    """Remove build artifacts.

    build_package writes every binary, `lib<name>.a` and manifest into
    `<pkg>/build/<profile>/` (get_output_dir), so removing those directories
    removes the build. Anything else under `<pkg>/build/` is left alone.
    A package reached through another tree's symlink builds (and runs its
    tests) under `ROOT/build/linked/` instead (#3818, #3831), and `build.py
    run` links each source under `ROOT/build/run/<digest>/` (#2252): both
    removed whole (#4167).
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

    for sub in ("linked", "run"):
        root_out = ROOT / "build" / sub
        if root_out.is_dir():
            shutil.rmtree(root_out)
            print(f"  🗑 {shown(root_out)}")

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

    try:
        return commands[args.command](args)
    except manifest.ManifestError as e:
        # file:line, not a traceback: the manifest is the user's to fix.
        print(f"error: {e}", file=sys.stderr)
        return 1
    except StrayTestsDirError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
