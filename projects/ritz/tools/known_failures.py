#!/usr/bin/env python3
"""The one known-failures schema, parser and outcome rule (AGAST #1834).

Every gate that may excuse a failure reads its excuses from
known-failures/<agast>.toml at the workspace root, one file per AGAST ticket:

    [[entry]]
    gate     = "matrix"            # which gate (GATES below)
    compiler = "ritz1"             # which compiler it is excused under
    unit     = "test_trait_bounds" # what failed, in the gate's own key
    reason   = "trait bounds on generic params"
    agast    = 1621                # must equal the file name

and decides with outcome().  Before #1834 there were six lists in four formats
(rz.toml [ci.known_failing.build], scripts/regression-known-failures{,-ritz1}
.txt, the matrix's EXPECTED_FAILURES, example_tests.py's KNOWN_FAILING,
tools/doc_known_failures/) and the hard / known / xpass rule was written three
times (rz gate_outcome, the matrix's matrix_outcome, regression.sh inline).

One file per ticket, not one file: a fix deletes its own ticket's file, so two
fixes never edit the same hunk and land in either order (AGAST #3963, which
split doc_known_failures/ for that reason).

The rules, all enforced here at load time so no gate can honour a bad excuse:
  * every entry cites its AGAST ticket, as `agast` and as the file name;
  * an excused unit that fails is advisory: printed with its ticket;
  * an excused unit that PASSES fails the gate (strict xpass), so the list
    only shrinks; an excused unit that did not run is neither;
  * an unexcused failure always gates.
And two gates have no name here, so nothing can excuse them: regression.sh's
Stage 5 (ritz1 vs ritz1_selfhosted accept sets, compared with no list at all)
and a test-side excuse for `rz test --all` (a behavioural failure is never
excusable; that sweep reads the `build` list).

CLI, for shell callers (regression.sh) and humans:
  known_failures.py verdict --gate G --compiler C UNIT STATUS
      STATUS is `pass` or anything else (a failure).  Prints one line:
      `pass`, `hard`, `known\\t<cite>` or `xpass\\t<cite>\\t<file>`.
  known_failures.py list --gate G --compiler C     `<unit>\\t<cite>` lines
  known_failures.py check                          validate every file
Exit 2, with nothing on stdout, on a malformed list or a bad argument, so a
caller that reads the verdict fails closed.  RITZ_KNOWN_FAILURES overrides the
directory (tests and scripts/prove-stage5-divergence.sh).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tomllib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]
DEFAULT_DIR = WORKSPACE / "known-failures"

COMPILERS = ("ritz0", "ritz1", "ritz1_selfhosted")

# gate -> (compilers an entry may name, what a unit is).  "any" means the
# gate's sweep does not vary by compiler, so neither does its excuse.
GATES: dict[str, tuple[tuple[str, ...], str]] = {
    "build": (("any",),
              "an rz project id (`rz build/test --all`, train.sh package tests)"),
    "matrix": (COMPILERS,
               ("`<file>` (excuses its build failures) or `<file>::<fn>` "
                "(tools/run_regression_matrix.py)")),
    # ritz1 covers ritz1_selfhosted too, and a selfhosted-only entry is
    # refused: the shared list is safe only because Stage 5 compares the two
    # accept sets with no list at all (scripts/regression.sh).
    "regression": (("ritz0", "ritz1"),
                   ("an example key, its path under examples/ with / as _ "
                    "(scripts/regression.sh)")),
    "examples": (("ritz0",),
                 "a test file under examples/ (tools/example_tests.py)"),
    "doc": (("ritz1", "ritz1_selfhosted"),
            "`<DOC.md> <12-hex block digest>` (tools/check_doc_examples.py)"),
}

NEVER_EXCUSED = {
    "stage5": "Stage 5 compares ritz1 and ritz1_selfhosted with no list: two "
              "compilers disagreeing is a self-hosting bug",
    "test": "a test failure is behavioural; `rz test --all` reads the build "
            "list for packages that cannot compile",
}

FIELDS = ("gate", "compiler", "unit", "reason", "agast")
_DOC_UNIT_RE = re.compile(r"\S+\.md [0-9a-f]{12}")


class KnownFailuresError(ValueError):
    """A malformed known-failures file; the message names file and entry."""


@dataclass(frozen=True)
class Entry:
    gate: str
    compiler: str
    unit: str
    reason: str
    agast: int
    path: Path = field(compare=False)

    @property
    def cite(self) -> str:
        """How every gate prints the excuse."""
        return f"AGAST #{self.agast}: {self.reason}"


def _check(path: Path, n: int, raw: object) -> Entry:
    where = f"{path.name} [[entry]] {n}"
    if not isinstance(raw, dict):
        raise KnownFailuresError(f"{where}: not a table")
    extra = sorted(set(raw) - set(FIELDS))
    if extra:
        raise KnownFailuresError(f"{where}: unknown field(s) {', '.join(extra)}; "
                                 f"an entry has exactly {', '.join(FIELDS)}")
    agast = raw.get("agast")
    if type(agast) is not int or agast <= 0:
        raise KnownFailuresError(
            f"{where}: agast must be the AGAST ticket tracking the failure, as a "
            f"positive integer (agast = 1234), got {agast!r}")
    if str(agast) != path.stem:
        raise KnownFailuresError(f"{where}: agast = {agast} but the file is {path.name}; "
                                 f"an entry lives in its ticket's file")
    for k in ("gate", "compiler", "unit", "reason"):
        v = raw.get(k)
        if not isinstance(v, str) or not v.strip():
            raise KnownFailuresError(f"{where}: {k} must be a non-empty string, got {v!r}")
    gate, compiler, unit = raw["gate"], raw["compiler"], raw["unit"]
    if gate in NEVER_EXCUSED:
        raise KnownFailuresError(f"{where}: gate {gate!r} is never excused: "
                                 f"{NEVER_EXCUSED[gate]}")
    if gate not in GATES:
        raise KnownFailuresError(f"{where}: unknown gate {gate!r}; "
                                 f"one of {', '.join(GATES)}")
    compilers, what = GATES[gate]
    if compiler not in compilers:
        raise KnownFailuresError(
            f"{where}: gate {gate!r} takes compiler {' or '.join(compilers)}, "
            f"got {compiler!r}")
    if gate == "doc" and not _DOC_UNIT_RE.fullmatch(unit):
        raise KnownFailuresError(f"{where}: unit {unit!r} is not {what}: "
                                 f"`<DOC.md> <12-hex digest>`")
    if gate == "matrix" and unit.count("::") > 1:
        raise KnownFailuresError(f"{where}: unit {unit!r} is not {what}")
    return Entry(gate, compiler, unit, raw["reason"].strip(), agast, path)


def load(directory: Path | None = None) -> list[Entry]:
    """Every entry under `directory` (default: RITZ_KNOWN_FAILURES, else
    known-failures/), validated.  Raises KnownFailuresError, naming the file,
    on anything malformed or a (gate, compiler, unit) listed twice."""
    if directory is None:
        directory = Path(os.environ.get("RITZ_KNOWN_FAILURES") or DEFAULT_DIR)
    directory = Path(directory)
    entries: list[Entry] = []
    seen: dict[tuple[str, str, str], Path] = {}
    if not directory.is_dir():
        return entries
    for path in sorted(directory.iterdir(), key=lambda p: p.name):
        if path.name.startswith(".") or path.name == "README.md":
            continue
        if path.suffix != ".toml" or not path.stem.isdigit():
            raise KnownFailuresError(
                f"{path.name}: name the file for its AGAST ticket, e.g. 1234.toml")
        try:
            doc = tomllib.loads(path.read_text())
        except tomllib.TOMLDecodeError as e:
            raise KnownFailuresError(f"{path.name}: not valid TOML: {e}") from None
        if set(doc) - {"entry"} or not isinstance(doc.get("entry", []), list):
            raise KnownFailuresError(f"{path.name}: expected only [[entry]] tables, "
                                     f"got {sorted(doc)}")
        for n, raw in enumerate(doc.get("entry", []), 1):
            e = _check(path, n, raw)
            key = (e.gate, e.compiler, e.unit)
            if key in seen:
                raise KnownFailuresError(f"{path.name} [[entry]] {n}: {key} is listed "
                                         f"twice (first in {seen[key].name})")
            seen[key] = path
            entries.append(e)
    return entries


def _list_compiler(gate: str, compiler: str) -> str:
    if gate not in GATES:
        raise KnownFailuresError(f"unknown gate {gate!r}; one of {', '.join(GATES)}")
    if gate == "build":
        return "any"
    if compiler not in COMPILERS:
        raise KnownFailuresError(f"unknown compiler {compiler!r}")
    if gate == "regression" and compiler == "ritz1_selfhosted":
        return "ritz1"
    return compiler


def entries_for(gate: str, compiler: str,
                entries: Iterable[Entry] | None = None) -> dict[str, Entry]:
    """{unit: Entry} excused for `gate` under `compiler`."""
    c = _list_compiler(gate, compiler)
    es = load() if entries is None else entries
    return {e.unit: e for e in es if e.gate == gate and e.compiler == c}


def known(gate: str, compiler: str,
          entries: Iterable[Entry] | None = None) -> dict[str, str]:
    """{unit: cite} excused for `gate` under `compiler`, in file order."""
    return {u: e.cite for u, e in entries_for(gate, compiler, entries).items()}


# ---------------------------------------------------------------------------
# The outcome
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Outcome:
    hard: list[str]          # failed, not excused: gates
    known: dict[str, str]    # failed unit -> the key excusing it: advisory
    xpass: list[str]         # keys excused but not failing that way: gates

    @property
    def ok(self) -> bool:
        return not self.hard and not self.xpass


def _same(key: str, unit: str) -> bool:
    return key == unit


def _any_failure(key: str, unit: str, status: str) -> bool:
    return True


def outcome(known: Iterable[str], results: Mapping[str, str], *,
            scope: Callable[[str, str], bool] = _same,
            covers: Callable[[str, str, str], bool] = _any_failure) -> Outcome:
    """Classify one sweep against its excuses.  The only copy of the rule.

    `known` are the excused keys, `results` maps every unit that RAN to its
    status, "pass" or a failure.  A key applies to the units in its `scope`
    (default: the unit of the same name), and excuses a failing one when
    `covers(key, unit, status)` (default: any failure).  A key whose units
    ran without a failure it covers is an xpass; one none of whose units ran
    is ignored, so a filtered sweep makes no xpass.  An exact key is
    preferred over a wider one.  Orders follow `results` (hard, known) and
    `known` (xpass).
    """
    keys = list(known)
    exact = set(keys)
    hard: list[str] = []
    excused: dict[str, str] = {}
    for unit, status in results.items():
        if status == "pass":
            continue
        if unit in exact and covers(unit, unit, status):
            excused[unit] = unit
            continue
        key = next((k for k in keys if k != unit and scope(k, unit)
                    and covers(k, unit, status)), None)
        if key is None:
            hard.append(unit)
        else:
            excused[unit] = key
    xpass = []
    for k in keys:
        units = [(u, s) for u, s in results.items() if scope(k, u)]
        if units and not any(s != "pass" and covers(k, u, s) for u, s in units):
            xpass.append(k)
    return Outcome(hard, excused, xpass)


# The matrix's keys (tools/run_regression_matrix.py): units are `file::fn`; a
# `file` key reaches every fn of the file but excuses only build-stage
# failures, which hit every fn at once; a runtime failure needs a per-fn key,
# or one line would be a bulk allowlist for the whole file.
MATRIX_BUILD_STATUSES = frozenset({"compile-fail", "asm-fail", "link-fail", "deps-fail"})


def matrix_scope(key: str, unit: str) -> bool:
    return unit == key or ("::" not in key and unit.startswith(key + "::"))


def matrix_covers(key: str, unit: str, status: str) -> bool:
    return unit == key or status in MATRIX_BUILD_STATUSES


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verdict", help="classify one unit's result")
    lst = sub.add_parser("list", help="the excused units of a gate")
    for p in (v, lst):
        p.add_argument("--gate", required=True)
        p.add_argument("--compiler", required=True)
    v.add_argument("unit")
    v.add_argument("status", help="`pass`, or anything else for a failure")
    sub.add_parser("check", help="validate every known-failures file")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "check":
            n = len(load())
            print(f"{n} known-failure entr{'y' if n == 1 else 'ies'}: ok", file=sys.stderr)
            return 0
        es = entries_for(args.gate, args.compiler)
        if args.cmd == "list":
            for u, e in es.items():
                print(f"{u}\t{e.cite}")
            return 0
        o = outcome(list(es) if args.unit in es else [], {args.unit: args.status})
        if o.hard:
            print("hard")
        elif o.known:
            print(f"known\t{es[args.unit].cite}")
        elif o.xpass:
            e = es[args.unit]
            try:
                where = e.path.relative_to(WORKSPACE)
            except ValueError:
                where = e.path
            print(f"xpass\t{e.cite}\t{where}")
        else:
            print("pass")
        return 0
    except KnownFailuresError as e:
        print(f"known_failures: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
