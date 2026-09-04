"""Determinism tests for source-file compile ordering (AGAST #1286).

Background: `ImportResolver.processed_files` is a `set`. Iterating it to build
the compile order made that order depend on CPython's per-process randomised
string hash seed, so `./rz build <project>` reported a *different* first
compiler error on every run against an unchanged tree.

These tests pin the contract that made that bug possible:

  1. `order_source_files` is a pure, total ordering — same inputs, same output,
     independent of the input container's iteration order.
  2. That ordering survives a fresh interpreter with a different
     `PYTHONHASHSEED`, which is the property the old code actually violated.

The unit tests are cheap and cover the ordering function directly. The
subprocess test is the decisive one: it is the only test here that would have
failed before the fix, because a set's iteration order is stable *within* a
process and only varies *across* processes.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from import_resolver import order_source_files  # noqa: E402

RITZ0_DIR = Path(__file__).parent
LIST_DEPS = RITZ0_DIR / "list_deps.py"

# Seeds chosen to give genuinely different string hashes. 0 disables
# randomisation entirely; the rest are arbitrary distinct nonzero seeds.
HASH_SEEDS = ["0", "1", "42", "12345", "99991"]


# --------------------------------------------------------------------------
# Unit tests: the ordering function itself
# --------------------------------------------------------------------------


@pytest.mark.unit
def test_main_file_is_last():
    """`build.py` splices extra sources in with `insert(-1, ...)`, so the
    entry point must be the final element."""
    files = {"/p/b.ritz", "/p/a.ritz", "/p/main.ritz"}
    assert order_source_files(files, "/p/main.ritz")[-1] == "/p/main.ritz"


@pytest.mark.unit
def test_imports_sorted_by_posix_path():
    files = {"/p/z.ritz", "/p/a.ritz", "/p/m.ritz", "/p/main.ritz"}
    assert order_source_files(files, "/p/main.ritz") == [
        "/p/a.ritz",
        "/p/m.ritz",
        "/p/z.ritz",
        "/p/main.ritz",
    ]


@pytest.mark.unit
def test_main_file_not_duplicated():
    """The entry point appears exactly once even though it is also a member
    of `processed_files` (the resolver adds it at line 1 of `resolve`)."""
    files = {"/p/a.ritz", "/p/main.ritz"}
    result = order_source_files(files, "/p/main.ritz")
    assert result.count("/p/main.ritz") == 1
    assert result == ["/p/a.ritz", "/p/main.ritz"]


@pytest.mark.unit
def test_order_independent_of_input_iteration_order():
    """The whole point: the caller's container order must not leak through.

    A plain `[f for f in some_set]` passes every other test in this file but
    fails this one, which is precisely the defect that shipped.
    """
    paths = [f"/p/mod_{i}.ritz" for i in range(50)]
    forward = order_source_files(paths + ["/p/main.ritz"], "/p/main.ritz")
    reverse = order_source_files(
        list(reversed(paths)) + ["/p/main.ritz"], "/p/main.ritz"
    )
    assert forward == reverse


@pytest.mark.unit
def test_missing_main_file_still_appended():
    """Defensive: the entry point is appended even if it was never added to
    `processed_files`, so callers can never get a list without it."""
    assert order_source_files({"/p/a.ritz"}, "/p/main.ritz") == [
        "/p/a.ritz",
        "/p/main.ritz",
    ]


@pytest.mark.unit
def test_empty_dependency_set():
    assert order_source_files(set(), "/p/main.ritz") == ["/p/main.ritz"]


# --------------------------------------------------------------------------
# Cross-process test: the regression that actually bit
# --------------------------------------------------------------------------


@pytest.fixture
def import_tree(tmp_path):
    """A module with enough imports that set iteration order visibly varies.

    Names are deliberately unsorted-looking and numerous — with only two or
    three imports, different hash seeds frequently happen to agree by chance.
    """
    names = [f"m{i:02d}" for i in range(24)]
    for name in names:
        (tmp_path / f"{name}.ritz").write_text(
            textwrap.dedent(
                f"""\
                fn {name}_value() -> i32
                    {int(name[1:])}
                """
            )
        )
    imports = "\n".join(f"import {name}" for name in names)
    main = tmp_path / "main.ritz"
    main.write_text(f"{imports}\n\nfn main() -> i32\n    0\n")
    return main


def _list_deps(main: Path, seed: str) -> str:
    """Run `list_deps.py` in a fresh interpreter with a pinned hash seed."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = seed
    # Avoid stale .pyc masking the seed effect; harmless otherwise.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, str(LIST_DEPS), str(main), "--project-root", str(main.parent)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, f"list_deps failed (seed={seed}): {proc.stderr}"
    return proc.stdout


@pytest.mark.integration
def test_dep_order_identical_across_hash_seeds(import_tree):
    """Same tree, different `PYTHONHASHSEED`, byte-identical dependency order.

    This is the assertion the build system needed and did not have: before the
    fix, `collect_all_source_files` iterated a `set`, and these runs disagreed.
    """
    outputs = {seed: _list_deps(import_tree, seed) for seed in HASH_SEEDS}

    baseline_seed, baseline = next(iter(outputs.items()))
    for seed, output in outputs.items():
        assert output == baseline, (
            f"dependency order differs between PYTHONHASHSEED={baseline_seed} "
            f"and PYTHONHASHSEED={seed}:\n"
            f"--- seed {baseline_seed} ---\n{baseline}\n"
            f"--- seed {seed} ---\n{output}"
        )


@pytest.mark.integration
def test_dep_order_is_sorted_with_main_last(import_tree):
    """The order is not merely stable, it is the documented one — so a future
    change that swaps in a different-but-stable order is caught here."""
    files = [line for line in _list_deps(import_tree, "0").splitlines() if line]

    assert Path(files[-1]).name == "main.ritz", "entry point must sort last"
    imports = files[:-1]
    assert imports == sorted(imports), "imports must be sorted by POSIX path"
    assert len(imports) == 24, f"expected 24 imports, got {len(imports)}"


# --------------------------------------------------------------------------
# Emitted-IR determinism (AGAST #1286, second defect)
# --------------------------------------------------------------------------

RITZ_ROOT = RITZ0_DIR.parent
RITZ0_MAIN = RITZ0_DIR / "ritz0.py"
# A real program that exercises monomorphization (generic Vec/Span usage).
IR_SAMPLE = RITZ_ROOT / "examples" / "tier4_applications" / "32_which" / "src" / "main.ritz"


def _emit_ir(tmp_path: Path, seed: str) -> str:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = seed
    env["RITZ_PATH"] = str(RITZ_ROOT)
    out = tmp_path / f"out_{seed}.ll"
    proc = subprocess.run(
        [sys.executable, str(RITZ0_MAIN), str(IR_SAMPLE), "-o", str(out), "--no-runtime"],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, f"compile failed (seed={seed}): {proc.stderr[-2000:]}"
    return out.read_text()


@pytest.mark.integration
def test_emitted_ir_identical_across_hash_seeds(tmp_path):
    """The compiler must emit byte-identical IR regardless of hash seed.

    `Monomorphizer._generate_specializations_iterative` used set comprehensions
    over `(base_name, type_args_key)` tuples to find pending instantiations.
    Set iteration order is hash-seed-dependent, and that order decided the order
    specialized structs/enums/functions were appended to the module — so the
    emitted `.ll` differed on every process. Measured before the fix: five
    distinct outputs from five seeds on this very program.

    Non-reproducible codegen undermines every content-hash the build system
    relies on, so this is pinned rather than left to chance.
    """
    # This used to be a `skipif(not IR_SAMPLE.exists())` — the same
    # collection-time-skip shape as AGAST #1327.  The sample is a tracked repo
    # file: if it goes missing that is a repo defect and must FAIL, not
    # silently drop the only reproducible-codegen coverage.
    assert IR_SAMPLE.exists(), (
        f"sample program {IR_SAMPLE} is missing — it is tracked in-repo, so "
        "this is a moved/deleted example, not an environment to skip for"
    )

    seeds = ["0", "1", "42", "777", "31337"]
    irs = {seed: _emit_ir(tmp_path, seed) for seed in seeds}

    baseline_seed, baseline = next(iter(irs.items()))
    for seed, ir in irs.items():
        assert ir == baseline, (
            f"emitted IR differs between PYTHONHASHSEED={baseline_seed} and "
            f"PYTHONHASHSEED={seed} ({len(baseline)} vs {len(ir)} bytes)"
        )
