"""pytest configuration for the ritz0 suite.

AGAST #1392. Two things live here, and they are independent.

1. `collect_ignore_glob` — a backstop, not the fix.

   Leaked test scratch directories used to be created inside the tree under
   test and contained a `ritzlib` symlink. When the package under test was
   ritzlib itself, the symlink pointed at its own ancestor and pytest's
   collector — which follows directory symlinks — walked a cycle. The suite
   burned 739 s and collected zero tests, against a 73 s baseline. Two such
   directories existed simultaneously, so the walk branched: the cost was
   exponential in depth, which is why it presented as "the suite got slow"
   rather than as an obvious hang.

   The actual fix is `test_runner.make_scratch_dir()`, which puts scratch under
   the system temp directory so the cycle is unconstructible. This glob exists
   so that a *future* leak — from an older checkout, a task-room worktree, or a
   third-party tool — degrades collection instead of wedging it. It is
   deliberately not the primary defence: an ignore rule that silently hides
   debris is how the original `.gitignore` entries came to paper over the same
   bug twice, once for the repo root and once for cryptosec.

2. `markers` — the suite decorates tests with `@pytest.mark.unit` and
   `@pytest.mark.integration`, which were unregistered. That emitted 99
   PytestUnknownMarkWarnings per run and, more importantly, meant `-m unit`
   silently selected on a typo'd name rather than erroring.
"""

collect_ignore_glob = [
    "tmp*",
    "ritz_test_*",
    "ritz_batch_test_*",
]


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "unit: fast, in-process test with no compiler subprocess"
    )
    config.addinivalue_line(
        "markers", "integration: drives a real compile/link/run subprocess"
    )
