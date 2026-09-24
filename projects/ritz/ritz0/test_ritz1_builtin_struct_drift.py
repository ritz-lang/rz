"""ritz1's hard-coded NFA structs must match their source definitions.

THE DEFECT (found by #1436's matrix gate)

ritz1's emitter does not use `struct NFA` from ritz1/src/nfa.ritz when it
compiles itself. It emits its own copy of the layout
(`emit_builtin_struct_types`: `%NFA = type { ... }`) and registers its own
field table (`register_builtin_structs`), and that copy shadows the source.

#1436 added `max_states` / `max_trans` to `struct NFA` and nowhere else.
ritz0 compiled everything fine, so every pytest and 199/199 doc blocks
passed; only ritz1 self-compiling nfa.ritz noticed:

    error: ritz1 cannot emit: unhandled EXPR_MEMBER      (x2, the two reads)

The reads failing was the lucky half. The two STORES in nfa_init compiled,
exit 0, to nothing at all — a field missing from the built-in table makes
`nfa.max_states = n` vanish without a diagnostic. A new field that is only
ever written would pass every gate in the repo while being silently dropped.

HOW

Static, because the failure mode being guarded against is precisely the one
no behavioural gate sees. For each NFA-family struct defined in ritz1/src:

  * the field names registered in `register_builtin_structs`, in order,
    must equal the source struct's field names, in order;
  * the `%Name = type { ... }` string must have the same number of members.

Field order in the registry is read from declaration order, which is how
every entry in that function is written (fN declared in order, then linked).
"""

import re
from pathlib import Path

import pytest

RITZ1_SRC = Path(__file__).resolve().parent.parent / "ritz1" / "src"
EMITTER = RITZ1_SRC / "emitter.ritz"

# The built-ins whose source definitions live in ritz1's own sources.
NFA_FAMILY = ["NFAFragment", "TokenPattern", "NFAState", "Transition", "NFA"]


def _source_fields(name: str) -> list[str]:
    """Field names of `struct <name>` from ritz1/src, in declaration order."""
    header = re.compile(rf"^struct {re.escape(name)}\s*$")
    for path in sorted(RITZ1_SRC.glob("*.ritz")):
        lines = path.read_text().splitlines()
        for i, line in enumerate(lines):
            if not header.match(line):
                continue
            fields = []
            for body in lines[i + 1 :]:
                if body.strip() == "" or body.lstrip().startswith("#"):
                    continue
                if not body[:1].isspace():
                    break  # dedent: end of struct body
                m = re.match(r"\s+(\w+)\s*:", body)
                assert m, f"{path.name}: unparsed field line in {name}: {body!r}"
                fields.append(m.group(1))
            return fields
    pytest.fail(f"no `struct {name}` in {RITZ1_SRC}")


def _registered_fields(name: str) -> list[str]:
    """Field names ritz1 registers for built-in <name>, in declaration order."""
    text = EMITTER.read_text()
    body = text[text.index("fn register_builtin_structs") :]
    end = body.index(f'make_struct(c"{name}",')
    # The entry for <name> starts after the previous make_struct(...) line.
    start = body.rfind("make_struct(", 0, end)
    start = body.index("\n", start) if start != -1 else 0
    return re.findall(r'make_\w*field\(c"(\w+)"', body[start:end])


def _llvm_member_count(name: str) -> int:
    m = re.search(rf'c"%{re.escape(name)} = type \{{ ([^}}]*) \}}', EMITTER.read_text())
    assert m, f"no `%{name} = type` string in {EMITTER.name}"
    return len([t for t in m.group(1).split(",") if t.strip()])


@pytest.mark.unit
@pytest.mark.parametrize("name", NFA_FAMILY)
def test_registered_fields_match_source(name):
    assert _registered_fields(name) == _source_fields(name), (
        f"ritz1's built-in {name} has drifted from its source definition; "
        f"update register_builtin_structs in emitter.ritz"
    )


@pytest.mark.unit
@pytest.mark.parametrize("name", NFA_FAMILY)
def test_llvm_type_matches_source(name):
    assert _llvm_member_count(name) == len(_source_fields(name)), (
        f"ritz1's `%{name} = type` has drifted from its source definition; "
        f"update emit_builtin_struct_types in emitter.ritz"
    )
