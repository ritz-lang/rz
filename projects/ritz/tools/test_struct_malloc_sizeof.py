"""Library code sizes every struct allocation with sizeof, never by hand (#4223, #4237).

Hand-counted sizes go stale as structs grow: tome's store_hash sized
HashEntry at 24 bytes (it is 56, #4210), pubsub sized PatternEntry at 40 (48)
and the channel table at 32 bytes a slot (ChannelEntry is 40), and valet's
compress allocated 270000 bytes for a GzipWriter/ZlibWriter of ~295 KB
(#4237).  ritzlib's malloc rounds small requests up to a size class, so an
overrun of a few bytes often lands in slack and no test sees it; this check
holds the rule at the source.

Rule: in ritzlib and every projects/*/lib, `malloc(ARG) as *T` for a struct
type T (a capitalised name) must have `sizeof(T)` in ARG, or ARG must name a
variable whose `let`/`var` definition a few lines above has `sizeof(T)`
(e.g. `let n: i64 = cap * sizeof(Slot)` then `malloc(n) as *Slot`).

A deliberate non-sizeof size goes in EXEMPT, keyed by (path, type), with the
reason.  There are none today.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECTS = Path(__file__).resolve().parents[2]

MALLOC_RE = re.compile(r"\bmalloc\((?P<arg>.*)\)\s+as\s+\*(?P<ty>[A-Z]\w*)\b")
IDENT_RE = re.compile(r"\b[a-z_]\w*\b")
LOOKBACK = 6

# (path relative to projects/, struct type) -> why its size isn't sizeof(T).
EXEMPT: dict[tuple[str, str], str] = {}


def lib_roots() -> list[Path]:
    """ritzlib plus every projects/*/lib, each real directory once.

    projects/ritzlib is a symlink to projects/ritz/ritzlib; resolving
    collapses the two.
    """
    roots: dict[Path, Path] = {}
    for root in [PROJECTS / "ritz" / "ritzlib", *sorted(PROJECTS.glob("*/lib"))]:
        if root.is_dir():
            roots.setdefault(root.resolve(), root)
    return list(roots.values())


def _sized_by_definition(lines: list[str], i: int, name: str, want: str) -> bool:
    """True if `name`'s nearest let/var definition above line i contains `want`."""
    def_re = re.compile(rf"\b(?:let|var)\s+{re.escape(name)}\b[^=]*=(.*)")
    for back in lines[max(0, i - LOOKBACK) : i][::-1]:
        dm = def_re.search(back.split("#", 1)[0])
        if dm:
            return want in dm.group(1)
    return False


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
            if any(
                _sized_by_definition(lines, i, name, want)
                for name in IDENT_RE.findall(arg)
            ):
                continue
            yield path.relative_to(root).as_posix(), i + 1, ty, line.strip()


@pytest.mark.unit
def test_lib_struct_mallocs_use_sizeof():
    bad = []
    for root in lib_roots():
        prefix = root.relative_to(PROJECTS).as_posix()
        for rel, ln, ty, line in unsized_struct_mallocs(root):
            if (f"{prefix}/{rel}", ty) in EXEMPT:
                continue
            bad.append(f"{prefix}/{rel}:{ln}: {line}  (want sizeof({ty}))")
    assert not bad, "struct allocations sized by hand:\n" + "\n".join(bad)


@pytest.mark.unit
def test_exemptions_are_still_needed():
    """An EXEMPT entry whose site now uses sizeof (or is gone) must be dropped."""
    live = {
        (f"{root.relative_to(PROJECTS).as_posix()}/{rel}", ty)
        for root in lib_roots()
        for rel, _, ty, _ in unsized_struct_mallocs(root)
    }
    stale = sorted(set(EXEMPT) - live)
    assert not stale, f"stale EXEMPT entries: {stale}"


@pytest.mark.unit
def test_scan_covers_ritzlib_and_every_project_lib():
    covered = {root.relative_to(PROJECTS).as_posix() for root in lib_roots()}
    assert "ritz/ritzlib" in covered
    assert "ritzlib" not in covered  # symlink to ritz/ritzlib, scanned once
    for lib in ("tome/lib", "valet/lib", "mausoleum/lib", "squeeze/lib"):
        assert lib in covered


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
        "    let w: *Big = malloc(270000) as *Big  # ~200KB\n"
        "    let fs: i64 = sizeof(Frame)\n"
        "    let fr: *Frame = malloc(fs * count as i64) as *Frame\n"
        "    let other: i64 = sizeof(Pat)\n"
        "    let wrong: *Frame = malloc(other * count) as *Frame\n"
    )
    found = [(ln, ty) for _, ln, ty, _ in unsized_struct_mallocs(tmp_path)]
    assert found == [(2, "Pat"), (4, "Slot"), (9, "Big"), (13, "Frame")]
