"""harness/integration_without_spawn.txt names real, marked tests (AGAST #4627).

spawn_guard lets the listed `integration` test functions start nothing.  An
entry that no longer names a test, or names one that lost its mark, lets
nothing off: it is dead weight that hides how far the list has drained.  So
each entry must resolve, statically, to an `integration`-marked test function
(by its decorator, its class's, or a module-level `pytestmark`).

Read-only and in-process: no `integration` mark, so `-m inproc` runs it.
"""

import ast
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parents[1]
ALLOWLIST = RITZ0_DIR / "harness" / "integration_without_spawn.txt"


def _entries() -> list:
    out = []
    for line in ALLOWLIST.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def _mentions_integration(nodes) -> bool:
    return any("integration" in ast.unparse(n) for n in nodes)


def _module_marked(tree: ast.Module) -> bool:
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets)
                and _mentions_integration([node.value])):
            return True
    return False


def _resolve(entry: str):
    """(found, marked) for `path::[Class::]name`."""
    path, *names = entry.split("::")
    src = RITZ0_DIR / path
    if not src.is_file() or not names:
        return False, False
    tree = ast.parse(src.read_text())
    marked = _module_marked(tree)
    scope = tree.body
    for i, name in enumerate(names):
        last = i == len(names) - 1
        kinds = (ast.FunctionDef, ast.AsyncFunctionDef) if last else (ast.ClassDef,)
        node = next((n for n in scope if isinstance(n, kinds) and n.name == name), None)
        if node is None:
            return False, False
        marked = marked or _mentions_integration(node.decorator_list)
        scope = getattr(node, "body", [])
    return True, marked


def test_entries_are_unique():
    entries = _entries()
    dupes = sorted({e for e in entries if entries.count(e) > 1})
    assert not dupes, f"listed twice in {ALLOWLIST.name}: {dupes}"


def test_entries_carry_no_parameters():
    # spawn_guard matches the function id: a `[param]` entry matches nothing.
    bad = [e for e in _entries() if "[" in e or "@" in e]
    assert not bad, f"{ALLOWLIST.name} lists functions, not parameters: {bad}"


@pytest.mark.parametrize("entry", _entries())
def test_entry_is_an_integration_marked_test(entry):
    found, marked = _resolve(entry)
    assert found, (
        f"{ALLOWLIST.name}: {entry} names no test function; remove the entry")
    assert marked, (
        f"{ALLOWLIST.name}: {entry} is no longer `integration`-marked, so "
        f"`-m inproc` runs it already; remove the entry")
