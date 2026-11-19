"""tome sizes every struct allocation with sizeof, never by hand (#4223).

Hand-counted sizes went stale as structs grew: store_hash sized HashEntry at
24 bytes (it is 56, #4210), pubsub sized PatternEntry at 40 (48) and the
channel table at 32 bytes a slot (ChannelEntry is 40).  ritzlib's malloc
rounds small requests up to a size class, so an overrun of a few bytes often
lands in slack and no test sees it; this check holds the rule at the source.

Rule: in projects/tome/lib, `malloc(ARG) as *T` for a struct type T (a
capitalised name) must have `sizeof(T)` in ARG or, when ARG is a bare name,
in that name's `let`/`var` definition a few lines above.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TOME_LIB = Path(__file__).resolve().parents[2] / "tome" / "lib"

MALLOC_RE = re.compile(r"\bmalloc\((?P<arg>.*)\)\s+as\s+\*(?P<ty>[A-Z]\w*)\b")
LOOKBACK = 6


def unsized_struct_mallocs(root: Path):
    """Yield (relpath, lineno, type, line) for each struct malloc not sized by sizeof(T)."""
    for path in sorted(root.rglob("*.ritz")):
        lines = path.read_text().splitlines()
        for i, line in enumerate(lines):
            code = line.split("#", 1)[0]
            m = MALLOC_RE.search(code)
            if not m:
                continue
            ty, arg = m.group("ty"), m.group("arg").strip()
            want = f"sizeof({ty})"
            if want in arg:
                continue
            if re.fullmatch(r"\w+", arg):
                def_re = re.compile(rf"\b(?:let|var)\s+{arg}\b[^=]*=(.*)")
                defined = None
                for back in lines[max(0, i - LOOKBACK) : i][::-1]:
                    dm = def_re.search(back.split("#", 1)[0])
                    if dm:
                        defined = dm.group(1)
                        break
                if defined is not None and want in defined:
                    continue
            yield path.relative_to(root).as_posix(), i + 1, ty, line.strip()


@pytest.mark.unit
def test_tome_struct_mallocs_use_sizeof():
    bad = [
        f"tome/lib/{rel}:{ln}: {line}  (want sizeof({ty}))"
        for rel, ln, ty, line in unsized_struct_mallocs(TOME_LIB)
    ]
    assert not bad, "struct allocations sized by hand:\n" + "\n".join(bad)


@pytest.mark.unit
def test_checker_flags_hand_sized_mallocs(tmp_path):
    (tmp_path / "a.ritz").write_text(
        "fn f()\n"
        "    let p: *Pat = malloc(40) as *Pat  # String(16) + ...\n"
        "    let size: i64 = cap * 32\n"
        "    t.slots = malloc(size) as *Slot\n"
        "    let ok: *Pat = malloc(sizeof(Pat)) as *Pat\n"
        "    let n: i64 = cap * sizeof(Slot)\n"
        "    t.slots = malloc(n) as *Slot\n"
        "    let raw: *u8 = malloc(64)\n"
    )
    found = [(ln, ty) for _, ln, ty, _ in unsized_struct_mallocs(tmp_path)]
    assert found == [(2, "Pat"), (4, "Slot")]
