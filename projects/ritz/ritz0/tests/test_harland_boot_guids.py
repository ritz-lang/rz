"""AGAST #4550: harland boot initialises its five EFI GUIDs in place.

`projects/harland/boot/src/main.ritz` used to declare the five EFI GUIDs as
zeroed `var`s and fill all 55 fields by hand in `init_guids()`, called from
`efi_main` and again from `load_kernel_from_fs`.  #4544 made ritz1 emit a
`[[packed]]` struct constant initialiser as a packed LLVM value, so the
hand-filling can go: each GUID becomes one in-place constant initialiser.

`[[packed]]` means the byte layout is exact.  ritz0 already lowered these
correctly, so it is the oracle here: both compilers must emit the same
16-byte image for each GUID, and each image must equal the spec value.

Before this change the globals are `zeroinitializer`, so every assertion
below fails; `init_guids` still exists and is still called.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
BOOT_SRC = RITZ_ROOT.parents[0] / "harland" / "boot" / "src" / "main.ritz"
# The loader imports boot_abi.* (AGAST #4578): projects/harland on RITZ_PATH
# resolves it as harland/boot_abi/src/<module>.ritz.
HARLAND = RITZ_ROOT.parents[0] / "harland"

# The EFI spec values.  EFI_GUID is {data1: u32, data2: u16, data3: u16,
# data4: [8]u8}, and the on-disk image is data1/data2/data3 little-endian
# followed by the eight data4 bytes verbatim.
GUIDS = {
    "loaded_image_guid": (0x5B1B31A1, 0x9562, 0x11D2,
                          (0x8E, 0x3F, 0x00, 0xA0, 0xC9, 0x69, 0x72, 0x3B)),
    "fs_guid": (0x964E5B22, 0x6459, 0x11D2,
                (0x8E, 0x39, 0x00, 0xA0, 0xC9, 0x69, 0x72, 0x3B)),
    "acpi20_guid": (0x8868E871, 0xE4F1, 0x11D3,
                    (0xBC, 0x22, 0x00, 0x80, 0xC7, 0x3C, 0x88, 0x81)),
    "acpi10_guid": (0xEB9D2D30, 0x2D88, 0x11D3,
                    (0x9A, 0x16, 0x00, 0x90, 0x27, 0x3F, 0xC1, 0x4D)),
    "gop_guid": (0x9042A9DE, 0x23DC, 0x4A38,
                 (0x96, 0xFB, 0x7A, 0xDE, 0xD0, 0x80, 0x51, 0x6A)),
}


def _expected_image(name: str) -> bytes:
    data1, data2, data3, data4 = GUIDS[name]
    return (data1.to_bytes(4, "little") + data2.to_bytes(2, "little")
            + data3.to_bytes(2, "little") + bytes(data4))


def _compile(compiler: str, ritz1_bin, tmp_path: Path) -> str:
    """Compile the boot source to LLVM IR; return the IR text."""
    work = tmp_path / compiler
    work.mkdir()
    out = work / "boot.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{HARLAND}")
    if compiler == "ritz0":
        proc = run_ritz0(["--no-runtime", str(BOOT_SRC), "-o", str(out)],
                         cwd=work, env=env, timeout=600)
    else:
        proc = subprocess.run(
            [str(ritz1_bin), str(BOOT_SRC), "-o", str(out)],
            cwd=work, env=env, capture_output=True, text=True, timeout=600,
        )
    assert proc.returncode == 0 and out.exists(), (
        f"{compiler} failed to compile the harland boot path:\n"
        f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    )
    return out.read_text()


def _guid_definition(ir: str, name: str) -> str:
    """The `@name = ... global ...` line's right-hand side."""
    pattern = re.compile(
        r'^@(?:"%s"|%s)\s*=\s*(.*\bglobal\b.*)$' % (re.escape(name), re.escape(name)),
        re.MULTILINE,
    )
    match = pattern.search(ir)
    assert match, f"no global definition for @{name} in the boot IR"
    line = match.group(1)
    assert "EfiGuid" in line, f"@{name} is not an EfiGuid global: {line[:200]}"
    return line


def _image(initialiser: str, name: str) -> bytes:
    """Decode the initialiser's field values into the 16-byte GUID image."""
    assert "<{" in initialiser and "}>" in initialiser, (
        f"@{name}: initialiser is not a packed `<{{ ... }}>` struct: "
        f"{initialiser[:200]}"
    )
    body = initialiser[initialiser.index("<{") + 2:initialiser.rindex("}>")]
    fields = re.findall(r"i32\s+(-?\d+)|i16\s+(-?\d+)|i8\s+(-?\d+)", body)
    # findall yields one group per entry: (i32, '', ''), ('', i16, ''), ...
    ints32 = [int(a) for a, _, _ in fields if a]
    ints16 = [int(b) for _, b, _ in fields if b]
    ints8 = [int(c) for _, _, c in fields if c]
    assert len(ints32) == 1, f"@{name}: expected one i32 (data1), got {ints32}"
    assert len(ints16) == 2, f"@{name}: expected two i16 (data2/data3), got {ints16}"
    assert len(ints8) == 8, f"@{name}: expected eight i8 (data4), got {ints8}"
    return ((ints32[0] & 0xFFFFFFFF).to_bytes(4, "little")
            + (ints16[0] & 0xFFFF).to_bytes(2, "little")
            + (ints16[1] & 0xFFFF).to_bytes(2, "little")
            + bytes(v & 0xFF for v in ints8))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(GUIDS))
def test_boot_guid_image_matches_spec(compiler, ritz1_bin, tmp_path, name):
    """Each GUID's emitted image is packed and exactly the spec 16 bytes."""
    ir = _compile(compiler, ritz1_bin, tmp_path)
    image = _image(_guid_definition(ir, name), name)
    assert image == _expected_image(name), (
        f"{compiler} @{name}: got {image.hex()}, want {_expected_image(name).hex()}"
    )


@pytest.mark.integration
def test_ritz0_and_ritz1_emit_identical_guid_images(ritz1_bin, tmp_path):
    """ritz0 is the oracle: every GUID image agrees between the compilers."""
    ritz0_ir = _compile("ritz0", ritz1_bin, tmp_path)
    ritz1_ir = _compile("ritz1", ritz1_bin, tmp_path)
    for name in GUIDS:
        ritz0_image = _image(_guid_definition(ritz0_ir, name), name)
        ritz1_image = _image(_guid_definition(ritz1_ir, name), name)
        assert ritz1_image == ritz0_image, (
            f"@{name}: ritz0 {ritz0_image.hex()} != ritz1 {ritz1_image.hex()}"
        )


@pytest.mark.integration
def test_boot_source_initialises_guids_in_place():
    """No hand-filling remains: `init_guids` is gone and each var has a literal."""
    source = BOOT_SRC.read_text()
    assert "init_guids" not in source, (
        "init_guids still exists in the boot source; the GUIDs should be "
        "initialised in place (and its call sites removed)"
    )
    for name in GUIDS:
        assert re.search(
            r"^var\s+%s\s*:\s*EfiGuid\s*=\s*EfiGuid\s*\{" % re.escape(name),
            source, re.MULTILINE,
        ), f"{name} is not declared with an in-place `EfiGuid {{ ... }}` initialiser"
