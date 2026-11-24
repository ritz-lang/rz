#!/usr/bin/env python3
"""List harland `-> i32` functions whose every result is 0 (AGAST #4600).

A function whose every `return` is `return 0` and whose last statement is
`return 0` (or a bare tail `0`) tells its caller nothing: it should return
nothing. LARB v4 (review/4/harland.md, M10) counted ~99 of them in
kernel/src + boot/src; #4600 brought them down and this script is the
ratchet (projects/ritz/tools/test_harland_always_zero.py), so new ones
can't creep back.

It reads source text only: a function is the `fn` line plus every following
line indented deeper (blank and comment lines skipped). It is deliberately
conservative: a tail that isn't a literal 0 (an if/else or match expression)
counts as "not always 0".

    python3 projects/harland/tools/always_zero.py            # list them
    python3 projects/harland/tools/always_zero.py --count    # just the count
    python3 projects/harland/tools/always_zero.py --check    # fail on one not in ALLOWED
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HARLAND = Path(__file__).resolve().parents[1]
TREES = ["kernel/src", "boot/src"]

# Always-0 fns that keep `-> i32`, each with why. The ratchet test fails on
# one not listed here, and on an entry that is no longer always-0.
ALLOWED = {
    # Its shape is #1887's (kernel_main's structure).
    "kernel_main": "#1887",
    # Declared through a cycle-breaking `extern fn` elsewhere: ritz0 lowers
    # a unit extern to void but a unit definition to i32, and a module that
    # holds both emits invalid IR (#4625). Make them unit when it lands.
    "ring_dump": "#4625",
    "lapic_eoi": "#4625",
    "lapic_watchdog_arm": "#4625",
    "lapic_watchdog_stop": "#4625",
    "irq_route_print_reason": "#4625",
    "waitq_wake_irq": "#4625",
}

FN = re.compile(r"^(\s*)(?:pub\s+)?fn\s+(\w+)\s*\(.*\)\s*->\s*i32\s*(?:#.*)?$")
RETURN = re.compile(r"^\s*return\b\s*(.*?)\s*(?:#.*)?$")
ZERO = re.compile(r"^\(?\s*0\s*\)?$")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_code(line: str) -> bool:
    s = line.strip()
    return bool(s) and not s.startswith("#")


def always_zero_fns(text: str) -> list[tuple[int, str]]:
    """(line, name) of each `-> i32` fn in text whose every result is 0."""
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        m = FN.match(line)
        if not m:
            continue
        base = len(m.group(1))
        body = []
        for nxt in lines[i + 1 :]:
            if not _is_code(nxt):
                continue
            if _indent(nxt) <= base:
                break
            body.append(nxt)
        if not body:
            continue  # extern / declaration
        returns = [RETURN.match(b) for b in body]
        values = [r.group(1) for r in returns if r]
        if any(not ZERO.match(v) for v in values):
            continue
        last = body[-1]
        r = RETURN.match(last)
        tail = r.group(1) if r else re.sub(r"\s*#.*$", "", last.strip())
        if ZERO.match(tail):
            out.append((i + 1, m.group(2)))
    return out


def scan(root: Path = HARLAND, trees=TREES) -> list[str]:
    """'path:line: name' for every always-0 `-> i32` fn under trees."""
    hits = []
    for tree in trees:
        for path in sorted((root / tree).rglob("*.ritz")):
            rel = path.relative_to(root)
            for n, name in always_zero_fns(path.read_text(encoding="utf-8")):
                hits.append(f"{rel}:{n}: {name}")
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--count", action="store_true", help="print only the count")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any always-0 fn is missing from ALLOWED")
    args = ap.parse_args(argv)
    hits = scan()
    if args.check:
        new = [h for h in hits if h.rsplit(": ", 1)[1] not in ALLOWED]
        print("\n".join(new) or f"ok: {len(hits)} always-0 fns, all allowed")
        return 1 if new else 0
    if args.count:
        print(len(hits))
    else:
        print("\n".join(hits))
        print(f"{len(hits)} always-0 `-> i32` fns", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
