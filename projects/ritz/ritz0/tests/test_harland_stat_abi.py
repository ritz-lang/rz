"""Harland's stat/fstat record is ritzlib's Stat (AGAST #4832).

Harland's stat (4) and fstat (5) fill Linux's x86-64 `struct stat`, so
ritzlib.fs `stat` and `Fd.stat` return one `Stat` type on both targets and a
program's "did the file change" check needs no per-target code. The kernel
can't import ritzlib.sys (its syscall tables are per target), so
kernel/src/fs/stat.ritz mirrors the struct field for field. These tests diff
the two declarations: a field renamed, retyped, reordered, added or dropped
on either side breaks the ABI silently otherwise, since the kernel writes
the record through a user pointer.

The behaviour (mode, size and mtime through a real boot) is indium's
stat_test, which tools/test_tier1_boot.sh requires on /tmp and /var.
"""

import re
from pathlib import Path

RITZ_ROOT = Path(__file__).resolve().parents[2]
SYS = RITZ_ROOT / "ritzlib" / "sys.ritz"
FD = RITZ_ROOT / "ritzlib" / "fd.ritz"
FS = RITZ_ROOT / "ritzlib" / "fs.ritz"
KERNEL_STAT = RITZ_ROOT.parent / "harland" / "kernel" / "src" / "fs" / "stat.ritz"

SIZES = {"i64": 8, "i32": 4}


def struct_fields(path: Path, name: str = "Stat") -> list[tuple[str, str]]:
    """`(field, type)` of `struct <name>` in `path`, in declaration order."""
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        if re.match(rf"(pub )?struct {name}\s*$", line):
            fields = []
            for body in lines[i + 1:]:
                m = re.match(r"    (\w+): (\w+)", body)
                if not m:
                    break
                fields.append((m.group(1), m.group(2)))
            return fields
    raise AssertionError(f"no struct {name} in {path}")


def preceding_attr(path: Path, decl: str) -> str:
    """The line before the one starting with `decl` (its attribute, if any)."""
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith(decl):
            return lines[i - 1]
    raise AssertionError(f"no `{decl}` in {path}")


def test_kernel_stat_mirrors_ritzlib_stat():
    ritzlib = struct_fields(SYS)
    kernel = struct_fields(KERNEL_STAT)
    assert kernel == ritzlib


def test_stat_is_linux_struct_stat_size():
    """144 bytes with no implicit padding: Linux x86-64's struct stat."""
    fields = struct_fields(SYS)
    offset = 0
    for name, ty in fields:
        size = SIZES[ty]
        assert offset % size == 0, f"{name} at {offset} is misaligned"
        offset += size
    assert offset == 144


def test_mirror_diff_sees_a_drifted_field(tmp_path):
    """The diff is not vacuous: a retyped kernel field shows."""
    drifted = tmp_path / "stat.ritz"
    drifted.write_text(KERNEL_STAT.read_text().replace("st_size: i64", "st_size: i32"))
    assert struct_fields(drifted) != struct_fields(SYS)


def test_stat_and_fd_stat_are_portable():
    """Stat, fs `stat` and `Fd.stat`'s fstat have a Harland path."""
    assert "target_os" not in preceding_attr(SYS, "struct Stat")
    assert "target_os" not in preceding_attr(FS, "pub fn stat(")
    assert re.search(r'\[\[target_os = "harland"\]\]\nfn fd_fstat\(', FD.read_text())
    assert re.search(r'\[\[target_os = "harland"\]\]\nfn fs_stat_impl\(', FS.read_text())
