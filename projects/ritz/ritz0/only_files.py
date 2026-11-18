"""pytest plugin: collect only the listed test files (AGAST #3623).

    --only-file=PATH   (repeatable) collect only these files, PATH relative to
                       the directory pytest runs in, and order their tests
                       as listed

The gate's likely-first pre-pass (tools/ci_local.py) runs ~60 ritz0 test
files.  Given as file arguments they cost every xdist worker ~8 s of
collection: pytest's Session.collect re-collects a file argument's parent
directory for each argument (a file named twice must run twice, so that
level is never cached), and each pass builds a Module node for all ~570
files in ritz0/.  60 arguments made ~34,000 nodes to keep 60.  The same
selection as an ignore hook is one directory walk: 0.8 s.

Everything that is not a listed file, or a directory holding one, is
ignored; a directory with no listed file is not even entered, as a file
argument would not enter it.  A listed path that does not exist is a usage
error (exit 4), as a missing file argument is.

The listed order is the order the tests are handed out in: this hook wraps
every other `pytest_collection_modifyitems`, so ritz0/conftest.py's stable
rank sort (slow, then xdist_group, then the rest) still applies on top.

Loaded by ritz0/conftest.py (`pytest_plugins`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

_files_key = pytest.StashKey[dict]()
_dirs_key = pytest.StashKey[frozenset]()


def pytest_addoption(parser):
    parser.getgroup("ritz").addoption(
        "--only-file", action="append", default=[], metavar="PATH",
        help="collect only this test file (repeatable), in the order given")


def pytest_configure(config):
    listed = config.getoption("only_file")
    if not listed:
        return
    base = config.invocation_params.dir
    files: dict[Path, int] = {}
    for rel in listed:
        path = (base / rel).resolve()
        if not path.is_file():
            raise pytest.UsageError(f"--only-file: file or directory not found: {rel}")
        files.setdefault(path, len(files))
    config.stash[_files_key] = files
    config.stash[_dirs_key] = frozenset(d for f in files for d in f.parents)


def pytest_ignore_collect(collection_path, config):
    files = config.stash.get(_files_key, None)
    if files is None:
        return None
    path = collection_path.resolve()
    if path in files or path in config.stash[_dirs_key]:
        return None  # not ours to keep: --ignore and friends still apply
    return True


@pytest.hookimpl(wrapper=True)
def pytest_collection_modifyitems(session, config, items):
    files = config.stash.get(_files_key, None)
    if files is not None:
        last = len(files)
        items.sort(key=lambda item: files.get(item.path.resolve(), last))
    return (yield)
