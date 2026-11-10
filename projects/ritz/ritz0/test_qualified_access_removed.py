"""AGAST #2591: `import pkg.aa` then `aa::f()` must be a located error, not a crash.

`::` was removed from Ritz in RERITZ (LANGUAGE_SPEC §10.2, §15.3): imported
names share one flat namespace, and enum variants are qualified with `.`. ritz1
has no `::` token, so it already rejects every `a::b`. ritz0 still parses
`a::b` into a `QualifiedIdent`, and unless the qualifier was an `import ... as`
alias nothing lowered it. The emitter then died with

    NotImplementedError: Expression: <class 'ritz_ast.QualifiedIdent'>

and a Python traceback. When the file *did* have an alias, an unknown qualifier
reached `raise RitzImportError(...)` in import_resolver.py, a name that module
never defines, so that path died with a `NameError` instead.

Both are now one `file:line:column` diagnostic from ritz0, and all three
compilers refuse the program. Whether an *aliased* `alias::item` should keep
working is AGAST #1624's decision, not this ticket's. ritz0 still resolves it,
so that is pinned here only so this change can't move it by accident.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from test_ritz1_for_iterable import SELFHOSTED_BIN

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = Path(__file__).resolve().parent / "ritz0.py"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

AA = """\
pub fn f() -> i32
    42
"""

# name -> (main.ritz, the `a::b` text, its line:column in main.ritz)
REJECTED = {
    # The ticket: a plain, non-selective import has no alias to qualify with.
    "plain_import": (
        "import pkg.aa\n\nfn main() -> i32\n    aa::f()\n", "aa::f", "4:5"),
    # An alias exists in the file, but not this one (was a NameError).
    "unknown_qualifier_beside_alias": (
        "import pkg.aa as aa\n\nfn main() -> i32\n    zz::f()\n", "zz::f", "4:5"),
    # The spec's own example: an enum variant written the pre-RERITZ way.
    "enum_variant": (
        "enum Color\n    Red\n    Green\n\nfn main() -> i32\n"
        "    let c = Color::Red\n    0\n", "Color::Red", "6:13"),
}


def _compile(compiler: str, ritz1_bin, tmp_path: Path, name: str, main: str):
    work = tmp_path / f"{name}_{compiler}"
    (work / "pkg").mkdir(parents=True)
    (work / "pkg" / "aa.ritz").write_text(AA)
    (work / "main.ritz").write_text(main)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = [sys.executable, str(RITZ0), "main.ritz", "-o", str(ll)]
    else:
        cmd = [str(ritz1_bin if compiler == "ritz1" else SELFHOSTED_BIN),
               "main.ritz", "-o", str(ll)]
    proc = subprocess.run(cmd, cwd=work, env=env, capture_output=True,
                          text=True, timeout=300)
    return proc, proc.stdout + proc.stderr, ll


@pytest.mark.parametrize("name", sorted(REJECTED))
def test_ritz0_reports_qualified_access_at_its_location(tmp_path, name):
    main, text, where = REJECTED[name]
    proc, out, _ = _compile("ritz0", None, tmp_path, name, main)
    assert proc.returncode != 0, out
    assert "Traceback" not in out, out
    assert f"main.ritz:{where}:" in out, out
    assert f"`{text}`" in out, out
    assert "removed in RERITZ" in out, out


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_every_compiler_refuses_qualified_access(ritz1_bin, tmp_path, compiler, name):
    main, _, _ = REJECTED[name]
    proc, out, ll = _compile(compiler, ritz1_bin, tmp_path, name, main)
    assert proc.returncode != 0, out
    assert not ll.exists(), f"{compiler} left an .ll behind:\n{out}"
    assert "Traceback" not in out, out
    # Located: names the file with a line and column (ritz1 points at the item
    # its parser gave up on, not the `::`: AGAST #2600).
    assert "main.ritz:" in out, out


def test_ritz0_aliased_qualified_call_is_unchanged(tmp_path):
    """AGAST #1624 owns `alias::item`; ritz0 still lowers it to `item`."""
    main = "import pkg.aa as aa\n\nfn main() -> i32\n    aa::f()\n"
    proc, out, ll = _compile("ritz0", None, tmp_path, "alias", main)
    assert proc.returncode == 0, out
    assert "call i32 @f()" in ll.read_text() or "@\"f\"" in ll.read_text(), ll.read_text()
