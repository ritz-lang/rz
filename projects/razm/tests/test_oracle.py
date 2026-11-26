"""The oracle driver itself: `as` against `as` agrees, and a perturbed
object or link is caught, field by field."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

import oracle
from oracle import (CORPUS_FILES, KERNEL_FILES, Reloc, Symbol, assemble_with_as,
                    compare_links, compare_objects, link_kernel, read_elf,
                    reloc_key)


def _obj_name(rel: str) -> str:
    return rel.replace("/", "__").removesuffix(".s") + ".o"


@pytest.fixture(scope="module")
def as_objects(tmp_path_factory) -> dict[str, tuple[Path, Path]]:
    """Each corpus file assembled twice by `as`, in separate runs."""
    out = {}
    for run in ("a", "b"):
        d = tmp_path_factory.mktemp(f"as-{run}")
        for rel in CORPUS_FILES:
            obj = d / _obj_name(rel)
            assemble_with_as(rel, obj)
            out.setdefault(rel, []).append(obj)
    return {rel: tuple(pair) for rel, pair in out.items()}


def test_corpus_is_frozen_in_the_package():
    for rel in CORPUS_FILES + [oracle.KERNEL_LINKER_SCRIPT]:
        assert (oracle.CORPUS / rel).is_file(), rel


@pytest.mark.parametrize("rel", CORPUS_FILES)
def test_as_matches_as(as_objects, rel):
    a, b = as_objects[rel]
    want = read_elf(a.read_bytes())
    assert want.e_type == oracle.ET_REL and want.e_machine == oracle.EM_X86_64
    assert compare_objects(want, read_elf(b.read_bytes())) == []


def test_incbin_fixture_carries_the_blob(as_objects):
    obj = read_elf(as_objects["synthetic/incbin.s"][0].read_bytes())
    rodata = next(s for s in obj.sections if s.name == ".rodata")
    blob = (oracle.CORPUS / "synthetic/blob.bin").read_bytes()
    assert rodata.data.startswith(blob)


def test_kernel_link_as_matches_as(as_objects, tmp_path):
    a, b = tmp_path / "a.elf", tmp_path / "b.elf"
    link_kernel([as_objects[rel][0] for rel in KERNEL_FILES], a)
    link_kernel([as_objects[rel][1] for rel in KERNEL_FILES], b)
    assert a.stat().st_size > 0
    assert compare_links(a, b) == []


# --- perturbations: each edits one field of an `as` object in memory -------

PERTURBED_FILE = "kernel/boot.s"   # sections, relocations and globals


def _patch(data: bytearray, off: int, fmt: str, fn) -> None:
    (old,) = struct.unpack_from(fmt, data, off)
    new = fn(old)
    assert new != old
    struct.pack_into(fmt, data, off, new)


def _data_section(obj):
    return next(s for s in obj.sections
                if s.type not in oracle.TABLE_TYPES and s.type != oracle.SHT_NOBITS
                and s.size > 0 and s.index > 0)


def _global_symbol(obj):
    return next(s for s in obj.symbols if s.binding != oracle.STB_LOCAL
                and s.section not in ("*UND*", "*ABS*"))


def _perturb_section_bytes(obj, data):
    s = _data_section(obj)
    _patch(data, s.data_off, "<B", lambda v: v ^ 0xFF)
    return f"section {s.name}: bytes differ"


def _perturb_section_align(obj, data):
    s = _data_section(obj)
    _patch(data, s.header_off + 48, "<Q", lambda v: max(v, 1) * 2)
    return f"section {s.name}: align"


def _perturb_section_flags(obj, data):
    s = _data_section(obj)
    _patch(data, s.header_off + 8, "<Q", lambda v: v ^ 0x1)   # SHF_WRITE
    return f"section {s.name}: flags"


def _perturb_reloc_addend(obj, data):
    r = obj.relocs[0]
    _patch(data, r.file_off + 16, "<q", lambda v: v + 4)
    return f"relocation in {r.section}"


def _perturb_reloc_offset(obj, data):
    r = obj.relocs[0]
    _patch(data, r.file_off, "<Q", lambda v: v + 1)
    return f"relocation in {r.section}"


def _perturb_reloc_type(obj, data):
    r = obj.relocs[0]
    # R_X86_64_32 <-> R_X86_64_32S, the pair a mode mix-up would swap.
    _patch(data, r.file_off + 8, "<I", lambda v: 11 if v != 11 else 10)
    return f"relocation in {r.section}"


def _perturb_symbol_value(obj, data):
    s = _global_symbol(obj)
    _patch(data, s.file_off + 8, "<Q", lambda v: v + 1)
    return f"symbol {s.name}: value"


def _perturb_symbol_binding(obj, data):
    s = _global_symbol(obj)
    _patch(data, s.file_off + 4, "<B", lambda v: (2 << 4) | (v & 0xF))   # weak
    return f"symbol {s.name}: binding"


def _perturb_symbol_size(obj, data):
    s = _global_symbol(obj)
    _patch(data, s.file_off + 16, "<Q", lambda v: v + 8)
    return f"symbol {s.name}: size"


PERTURBATIONS = [_perturb_section_bytes, _perturb_section_align,
                 _perturb_section_flags, _perturb_reloc_addend,
                 _perturb_reloc_offset, _perturb_reloc_type,
                 _perturb_symbol_value, _perturb_symbol_binding,
                 _perturb_symbol_size]


@pytest.mark.parametrize("perturb", PERTURBATIONS, ids=lambda f: f.__name__[9:])
def test_perturbed_object_is_caught(as_objects, perturb):
    raw = as_objects[PERTURBED_FILE][0].read_bytes()
    want = read_elf(raw)
    assert want.relocs, "the perturbed file needs relocations"
    data = bytearray(raw)
    expect = perturb(want, data)
    diffs = compare_objects(want, read_elf(bytes(data)))
    assert any(expect in d for d in diffs), diffs


def test_missing_symbol_is_caught(as_objects):
    want = read_elf(as_objects[PERTURBED_FILE][0].read_bytes())
    got = read_elf(as_objects[PERTURBED_FILE][0].read_bytes())
    gone = _global_symbol(got)
    got.symbols.remove(gone)
    assert f"symbol {gone.name}: missing" in compare_objects(want, got)


def test_perturbed_kernel_link_is_caught(as_objects, tmp_path):
    objs = [as_objects[rel][0] for rel in KERNEL_FILES]
    victim = objs[1]
    obj = read_elf(victim.read_bytes())
    text = next(s for s in obj.sections if s.name == ".text")
    data = bytearray(victim.read_bytes())
    _patch(data, text.data_off, "<B", lambda v: v ^ 0xFF)
    bad = tmp_path / victim.name
    bad.write_bytes(bytes(data))
    a, b = tmp_path / "a.elf", tmp_path / "b.elf"
    link_kernel(objs, a)
    link_kernel([bad if o == victim else o for o in objs], b)
    assert compare_links(a, b)


# --- relocation target normalization ---------------------------------------

def _sym(name, section, value, binding=oracle.STB_LOCAL, typ=0):
    return Symbol(name, section, value, 0, typ, binding, 0)


def test_section_symbol_and_local_label_on_one_byte_are_equal():
    via_section = Reloc(".text", 4, 2, _sym(".data", ".data", 0, typ=oracle.STT_SECTION), 0x18, 0)
    via_label = Reloc(".text", 4, 2, _sym("msg", ".data", 0x10), 0x8, 0)
    assert reloc_key(via_section) == reloc_key(via_label)


def test_global_target_compares_by_name_not_value():
    a = Reloc(".text", 4, 4, _sym("f", ".text", 0x10, binding=1), -4, 0)
    b = Reloc(".text", 4, 4, _sym("f", ".text", 0x20, binding=1), -4, 0)
    c = Reloc(".text", 4, 4, _sym("g", ".text", 0x10, binding=1), -4, 0)
    assert reloc_key(a) == reloc_key(b)
    assert reloc_key(a) != reloc_key(c)
