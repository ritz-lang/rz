"""Enums are AST nodes, not a global tracker (AGAST #3994).

ritz1 used to record every enum in ast_helpers' parallel global arrays
(`g_enum_names`, `g_enum_variant_starts`, ...): 192 identifiers, sixteen
arrays, and nothing in the AST.  #3994 replaced them with EnumDef /
EnumVariant nodes under `Module.enums`.  This test pins the structural
acceptance so the tracker cannot creep back: no `g_enum_` global, the two
node structs, and `Module.enums`.

It fails on the pre-#3994 tree by construction — that is the point.  The
behaviour is covered by the regression matrix (ritz0/test/test_issue_enum_*),
which runs the enum corpus on ritz0, ritz1 and ritz1_selfhosted.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parent.parent / "ritz1" / "src"


def read(name):
    return (SRC / name).read_text()


def test_no_enum_tracker_globals():
    """No `g_enum_*` identifier survives anywhere in ritz1's sources."""
    offenders = []
    for path in sorted(SRC.glob("*.ritz")):
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if "g_enum_" in line:
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert offenders == [], "enum tracker globals are back:\n" + "\n".join(offenders)


def test_ast_declares_enum_nodes():
    """EnumDef and EnumVariant are AST node structs (ast.ritz)."""
    ast = read("ast.ritz")
    assert re.search(r"^struct EnumDef\b", ast, re.M), "ast.ritz has no EnumDef"
    assert re.search(r"^struct EnumVariant\b", ast, re.M), "ast.ritz has no EnumVariant"


def test_module_owns_the_enum_list():
    """Module.enums is the enum list the parser builds and imports merge."""
    ast = read("ast.ritz")
    module = ast[ast.index("struct Module") :]
    assert re.search(r"^  enums: \*EnumDef\b", module, re.M), "Module has no enums"

    helpers = read("ast_helpers.ritz")
    # The parse actions append to the module being built...
    assert "p.module.enums" in helpers, "enum_def actions do not build Module.enums"

    # ...and the import merge appends the imported module's enums.
    main = read("main.ritz")
    merge = main[main.index("fn merge_module_into") :]
    assert "other.enums" in merge, "merge_module_into drops imported enums"
