"""AGAST #3632: a freestanding [[bin]] records its provenance and is not
rebuilt when nothing it was built from changed.

Hosted binaries have had `<name>.manifest.json` and the up-to-date fast path
since AGAST #1382; compile_freestanding_binary (kernels, bootloaders, UEFI
apps) recompiled and relinked every time and wrote no manifest. Its manifest
holds what decides a freestanding binary's bytes beyond the hosted ones: the
object flags of its target, its .s files (and what they .incbin), its linker
script, the PIC / UEFI / link_runtime choices. Change any, and it rebuilds.

ritz0 is stubbed (it writes a fixed `_start`); clang and the linker are real.
"""

import importlib.util
import itertools
import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

cas = importlib.import_module("cas")

needs_toolchain = pytest.mark.skipif(
    not (shutil.which("clang") and (shutil.which("ld.lld") or shutil.which("ld"))
         and shutil.which("as")),
    reason="clang, as and a linker are needed")

IR = "define void @_start() {\n  ret void\n}\n"
STUB = ("#!{python}\nimport sys\nargs = sys.argv[1:]\n"
        "open(args[args.index('-o') + 1], 'w').write({ir!r})\n")
_LOADS = itertools.count()


@pytest.fixture
def buildpy(tmp_path, monkeypatch):
    monkeypatch.setenv(cas.CAS_DIR_ENV, str(tmp_path / "cas"))
    monkeypatch.delenv(cas.STATS_LOG_ENV, raising=False)
    monkeypatch.setenv("RITZ_PATH", str(PKG_DIR))
    spec = importlib.util.spec_from_file_location(
        f"ritz_buildpy_3632_fs_{next(_LOADS)}", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.get_build_cache("ritz0")._cache_dir = tmp_path / ".ritz-cache"
    stub = tmp_path / "ritz0_stub.py"
    stub.write_text(STUB.format(python=sys.executable, ir=IR))
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(mod, "RITZ0", stub)
    return mod


@pytest.fixture
def kernel(tmp_path):
    pkg = tmp_path / "fs_pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "kern.ritz").write_text("fn _start()\n    return\n")
    (pkg / "boot.s").write_text(".text\n.globl boot_marker\nboot_marker:\n    ret\n")
    (pkg / "link.ld").write_text("ENTRY(_start)\nSECTIONS { . = 0x100000; "
                                 ".text : { *(.text*) } }\n")
    (pkg / "build").mkdir()
    return pkg


class Builds:
    """Builds the kernel, counting the builds that compiled anything."""

    def __init__(self, buildpy, pkg, monkeypatch):
        self.b, self.pkg, self.compiles = buildpy, pkg, 0
        self.rebuilds = 0
        real = buildpy.compile_modules

        def counting(*a, **kw):
            self.compiles += 1
            return real(*a, **kw)
        monkeypatch.setattr(buildpy, "compile_modules", counting)

    def config(self, **over):
        kw = dict(name="kern", src_path=self.pkg / "src" / "kern.ritz",
                  additional_sources=[], freestanding=True,
                  target="x86_64-unknown-none", no_red_zone=True,
                  asm_files=[self.pkg / "boot.s"], linker_script=self.pkg / "link.ld")
        kw.update(over)
        return self.b.BinaryConfig(**kw)

    def __call__(self, use_cache=True, **over):
        def on_rebuild():
            self.rebuilds += 1
        out = self.b.compile_freestanding_binary(
            self.config(**over), self.pkg / "build", self.pkg, use_cache=use_cache,
            source_roots=["src"], on_rebuild=on_rebuild)
        assert out is not None, "the kernel did not build"
        return out


@pytest.fixture
def build(buildpy, kernel, monkeypatch):
    return Builds(buildpy, kernel, monkeypatch)


@pytest.mark.unit
@needs_toolchain
def test_a_freestanding_binary_records_its_provenance(build):
    elf = build()
    record = json.loads(build.b.binary_manifest_path(elf).read_text())
    assert record["binary_sha256"] == build.b._sha256_file(elf)
    assert [Path(s).name for s, _ in record["sources"]] == ["kern.ritz"]
    assert [Path(a[0]).name for a in record["asm"]] == ["boot.s"]
    assert Path(record["linker_script"][0]).name == "link.ld"
    assert record["target"]["objects"]["clang"][0] == "--target=x86_64-unknown-none"


@pytest.mark.unit
@needs_toolchain
def test_an_unchanged_kernel_is_not_rebuilt(build):
    elf = build()
    before = elf.read_bytes()
    assert build() == elf
    assert (build.compiles, build.rebuilds) == (1, 1), "rebuilt an up-to-date kernel"
    assert elf.read_bytes() == before


@pytest.mark.unit
@needs_toolchain
@pytest.mark.parametrize("change", ["source", "asm", "incbin", "linker_script",
                                    "flags", "pic", "binary", "manifest"])
def test_a_change_rebuilds(build, change):
    pkg = build.pkg
    over = base = {}
    if change == "pic":
        # A -linux target compiles -fPIC either way, so `pic` changes only
        # the link (--pie): the objects' flags cannot stand in for it.
        base = {"target": "x86_64-unknown-linux"}
    if change == "incbin":
        (pkg / "blob.bin").write_bytes(b"v1")
        (pkg / "boot.s").write_text('.data\n.incbin "blob.bin"\n')
    elf = build(**base)
    if change == "source":
        (pkg / "src" / "kern.ritz").write_text("fn _start()\n    return\n\n")
    elif change == "asm":
        (pkg / "boot.s").write_text(".text\n.globl other\nother:\n    ret\n")
    elif change == "incbin":
        (pkg / "blob.bin").write_bytes(b"v2")
    elif change == "linker_script":
        (pkg / "link.ld").write_text("ENTRY(_start)\nSECTIONS { . = 0x200000; "
                                     ".text : { *(.text*) } }\n")
    elif change == "flags":
        over = {"no_red_zone": False}
    elif change == "pic":
        over = dict(base, pic=True)
    elif change == "binary":
        elf.write_bytes(elf.read_bytes() + b"\0")
    elif change == "manifest":
        build.b.binary_manifest_path(elf).write_text("{}")
    build(**over)
    assert build.rebuilds == 2, f"a {change} change did not rebuild"


@pytest.mark.unit
@needs_toolchain
def test_no_cache_always_rebuilds(build):
    build()
    build(use_cache=False)
    assert build.rebuilds == 2


@pytest.mark.unit
@needs_toolchain
def test_build_package_says_up_to_date(buildpy, kernel, capsys):
    config = {"package": {"name": "fs_pkg"},
              "bin": [{"name": "kern", "path": "src/kern.ritz", "freestanding": True,
                       "target": "x86_64-unknown-none",
                       "kern": {"linker": {"script": "link.ld"},
                                "asm": {"files": ["boot.s"]}}}]}
    assert buildpy.build_package(kernel, config).ok
    first = capsys.readouterr().out
    assert "🔨 kern <- src/kern.ritz (x86_64-unknown-none, 1 asm files)" in first
    assert buildpy.build_package(kernel, config).ok
    second = capsys.readouterr().out
    assert "🔨" not in second
    assert "= kern up to date: " in second
