"""AGAST #3904: sema_walk.ritz is laid out so two Sema rooms' additions don't abut.

THE PROBLEM

Every #1816 room adds an import and a walk call to ritz1's sema_walk.ritz.
They used to land in the same spot: imports appended after the last one,
calls appended after the last check of a run.  git merges two insertions
cleanly when an unchanged line separates them.  It conflicts when they land
at the same point, or when one edits a line the other's insertion touches.

THE LAYOUT (no behaviour change)

- The project imports are one per line, in name order, each its own
  paragraph.  A new check's import goes at its sorted place, so two rooms
  meet only if their names sort between the same two neighbours.
- Each check's call in the walk (with its `if` guard, if it has one) is its
  own paragraph.  A new call is a new paragraph, so it never touches a line
  another room edits.  The calls stay in their order: that order is the
  order the errors are reported in.

THE TESTS

Both read the source; neither compiles.  Each is red on the base.
"""

import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "ritz1" / "src"
WALK = SRC / "sema_walk.ritz"

# Modules sema_walk imports for its own plumbing, not for a check.
CORE = {"ast", "ast_helpers", "emitter_core", "sema", "sema_type"}

IMPORT = re.compile(r"^import (\S+)")
FN_DEF = re.compile(r"^(?:pub )?fn (\w+)\(", re.M)


def _lines():
    return WALK.read_text().split("\n")


def _project_imports(lines):
    """(line index, module) for each import that isn't ritzlib's."""
    out = []
    for i, line in enumerate(lines):
        m = IMPORT.match(line)
        if m and not m.group(1).startswith("ritzlib."):
            out.append((i, m.group(1)))
    return out


def _check_fns(lines):
    """Every fn defined by a check module sema_walk imports."""
    names = set()
    for _, mod in _project_imports(lines):
        if mod in CORE:
            continue
        names.update(FN_DEF.findall((SRC / f"{mod}.ritz").read_text()))
    return names


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _units(lines, start, end, depth):
    """The sibling statements at `depth` in lines[start:end].

    Each unit is (first, last, heads): its leading comments, its line and
    every deeper line, with an `else` / `else if` folded into the `if`
    before it.  `first` is its first comment or statement line; `heads` its
    statement line and each `else` line, each opening a block of its own.
    """
    units = []
    i = start
    pending = None  # first line of a run of comments before a statement
    while i < end:
        line = lines[i]
        s = line.strip()
        if not s:
            pending = None
            i += 1
            continue
        if _indent(line) != depth:
            i += 1
            continue
        if s.startswith("#"):
            if pending is None:
                pending = i
            i += 1
            continue
        j = i + 1
        while j < end and (not lines[j].strip() or _indent(lines[j]) > depth):
            j += 1
        last = j - 1
        while not lines[last].strip():
            last -= 1
        if s.startswith("else") and units:
            first, _, heads = units.pop()
            heads = heads + [i]
        else:
            first = pending if pending is not None else i
            heads = [i]
        units.append((first, last, heads))
        pending = None
        i = j
    return units


def _classify(body, checks):
    calls_check = walks = False
    for line in body:
        s = line.strip()
        if s.startswith("#"):
            continue
        for name in re.findall(r"(\w+)\(", s):
            if name.startswith("sema_walk"):
                walks = True
            elif name in checks:
                calls_check = True
    return calls_check, walks


def _abutting(lines):
    """Adjacent sibling statements that both run a check and walk nothing."""
    checks = _check_fns(lines)
    bad = []

    def visit(start, end, depth):
        units = _units(lines, start, end, depth)
        prev = None
        for first, last, heads in units:
            calls_check, walks = _classify(lines[first : last + 1], checks)
            is_check = calls_check and not walks
            if prev is not None and is_check and prev[1] and first == prev[0] + 1:
                bad.append(f"line {first + 1}: {lines[first].strip()}")
            prev = (last, is_check)
            # Recurse into each block the statement opens.
            for h, nxt in zip(heads, heads[1:] + [last + 1]):
                inner = [k for k in range(h + 1, nxt) if lines[k].strip()]
                if inner:
                    visit(h + 1, nxt, min(_indent(lines[k]) for k in inner))

    fn_starts = [i for i, l in enumerate(lines) if FN_DEF.match(l)]
    for n, s in enumerate(fn_starts):
        e = fn_starts[n + 1] if n + 1 < len(fn_starts) else len(lines)
        visit(s + 1, e, 4)
    return bad


@pytest.mark.unit
def test_imports_sorted_one_paragraph_each():
    lines = _lines()
    imports = _project_imports(lines)
    names = [m for _, m in imports]
    assert names == sorted(names), f"sema_walk's imports aren't in name order: {names}"
    for (a, ma), (b, mb) in zip(imports, imports[1:]):
        gap = lines[a + 1 : b]
        assert any(not l.strip() for l in gap), (
            f"`import {ma}` and `import {mb}` abut (line {a + 1}): "
            "separate them with a blank line"
        )


@pytest.mark.unit
def test_check_calls_one_paragraph_each():
    bad = _abutting(_lines())
    assert not bad, (
        "sema_walk check calls that abut the check before them; give each "
        "its own paragraph:\n" + "\n".join(bad)
    )
