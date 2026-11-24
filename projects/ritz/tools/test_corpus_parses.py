"""Every tracked .ritz file under projects/ lexes and parses (AGAST #4042).

No gate checks that a tracked .ritz file parses unless some package builds it,
which is how ~50 dead files that no longer parsed built up unnoticed (#2229,
#3610). This runs ritz0's lexer and parser alone over `git ls-files
'projects/**.ritz'`: no import resolution, no type checking, so a file needs
no package context (--deps, RITZ_PATH, --target-os) to pass. The only skip is
rz.toml's [workspace.exclude] entry for docs/archive (retired code). There is
no allowlist: a file that doesn't parse gets fixed or deleted.

SHARDS test cases, not one per file (docs/TESTING.md, "What a ritz0 pytest
case costs"). Parsing ~1,350 files is ~15 CPU-s, so each case's child process
spreads its share over a fork pool; the child also keeps ritz0's
`parser`/`lexer` modules out of this process's sys.modules. One case was the
long pole of `make tools-ratchets` under xdist (~15 s, AGAST #4672); the
shards (every SHARDS-th file of the sorted list) let the workers share it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

WORKSPACE = Path(__file__).resolve().parents[3]
RITZ0 = WORKSPACE / "projects" / "ritz" / "ritz0"

# Retired code nothing builds (rz.toml [workspace.exclude], AGAST #1405).
ARCHIVE = "projects/ritz/docs/archive"

# Runs in a child: parse every path read from stdin, print the failures as
# JSON [[path, message], ...]. Each pool worker is forked after ritz0's
# parser is imported, so it pays the import once.
_CHILD = r"""
import json, os, sys
from multiprocessing import get_context
sys.path.insert(0, sys.argv[1])
from parser import parse

def check(path):
    try:
        with open(path, encoding="utf-8") as f:
            parse(f.read(), path)
    except Exception as e:  # LexerError, ParseError, or a parser crash
        return [path, f"{type(e).__name__}: {e}"]
    return None

paths = sys.stdin.read().split()
with get_context("fork").Pool(min(4, os.cpu_count() or 1)) as pool:
    bad = [r for r in pool.map(check, paths, chunksize=16) if r]
print(json.dumps(bad))
"""


SHARDS = 4


def corpus() -> list[str]:
    files = subprocess.run(
        ["git", "ls-files", "projects/**.ritz"], cwd=WORKSPACE,
        capture_output=True, text=True, check=True,
    ).stdout.split()
    return [f for f in files if not f.startswith(ARCHIVE + "/")]


@pytest.mark.parametrize("shard", range(SHARDS), ids=lambda i: f"shard{i}of{SHARDS}")
def test_every_tracked_ritz_file_parses(shard):
    # The one skip must stay rz.toml's archive exclusion, not drift from it.
    exclude = tomllib.loads((WORKSPACE / "rz.toml").read_text())["workspace"]["exclude"]
    assert ARCHIVE in exclude, f"{ARCHIVE} is no longer in rz.toml [workspace.exclude]"

    files = corpus()
    # Guard the walk: an empty or truncated list would pass vacuously.
    assert len(files) > 1000, f"only {len(files)} tracked .ritz files found"
    mine = sorted(files)[shard::SHARDS]
    assert mine, shard

    proc = subprocess.run(
        [sys.executable, "-c", _CHILD, str(RITZ0)], check=False, cwd=WORKSPACE,
        input="\n".join(mine), capture_output=True, text=True, timeout=300,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert proc.returncode == 0, proc.stderr[-4000:]
    bad = json.loads(proc.stdout)
    assert not bad, (
        f"{len(bad)} tracked .ritz file(s) don't parse; fix or delete them "
        "(no allowlist, AGAST #4042):\n" + "\n".join(f"  {m}" for _, m in bad))
