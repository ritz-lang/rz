"""Who writes each object: rllvm for `.ll`, razm for `.s` (AGAST #4808).

projects/razm/DESIGN.md "Cutover". Fake `rllvm`, `razm`, `clang` and `as`
programs stand in for the real ones (RITZ_RLLVM / RITZ_RAZM, and a PATH
entry), each logging its argv, so every rule is checked without compiling
anything:

* routing: rllvm exit 0 uses its object; exit 2 compiles the file with
  clang, same flags, after one line naming the file and construct; exit 1,
  a signal or a timeout fails the build with no fallback, and unlinks the
  partial object; rllvm runs under clang's address-space cap;
* the switches: RITZ_OBJ_PRODUCER=clang, RITZ_ASM_PRODUCER=as; UEFI is
  always clang;
* the keys: the producer is in cas_module_key, cas_harness_key, both
  binary provenances (razm's sha256 next to each .s), and the shim's
  `<obj>.producer` stamp, written after the object is replaced.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
import textwrap
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG_DIR))

# Every test runs a fake tool (or `clang --version`): a process each.
pytestmark = pytest.mark.integration

HOSTED = ["-c", "-O2", "-fPIC", "-ffreestanding", "-fno-builtin"]
# A small-PIC userland module's flags (freestanding_target): what rllvm takes.
PIC = ["-c", "--target=x86_64-unknown-none", "-ffreestanding", "-fno-builtin",
       "-march=native", "-msha", "-fPIC"]
# Harland's kernel modules: clang's until rllvm's frames fit 4 KiB stacks.
KERNEL = ["-c", "--target=x86_64-none-elf", "-ffreestanding", "-fno-builtin",
          "-march=native", "-msha", "-mcmodel=kernel", "-mno-red-zone"]
UEFI = ["-c", "--target=x86_64-unknown-windows-gnu", "-fshort-wchar"]

# A fake tool: logs argv (and its RLIMIT_AS) as one JSON line, then acts on
# $FAKE_<NAME>_MODE: ok (write the -o file), unsupported (exit 2 with
# rllvm's message), fail (partial object, exit 1), segv, sleep.
FAKE = textwrap.dedent("""\
    #!{python}
    import json, os, resource, signal, sys, time
    name = {name!r}
    args = sys.argv[1:]
    if args == ["--version"]:
        print(name + " version 99.fake"); sys.exit(0)
    with open({log!r}, "a") as f:
        f.write(json.dumps({{"tool": name, "args": args, "cwd": os.getcwd(),
                             "as_limit": resource.getrlimit(resource.RLIMIT_AS)[0]}}) + "\\n")
    mode = os.environ.get("FAKE_" + name.upper() + "_MODE", "ok")
    out = args[args.index("-o") + 1] if "-o" in args else None
    if mode == "ok":
        open(out, "wb").write(("obj by " + name).encode()); sys.exit(0)
    if mode == "unsupported":
        sys.stderr.write("rllvm: " + args[-3] + ":11: unsupported: type 'metadata'\\n")
        sys.exit(2)
    if mode == "fail":
        open(out, "wb").write(b"partial")
        sys.stderr.write(name + ": deliberate failure\\n"); sys.exit(1)
    if mode == "segv":
        open(out, "wb").write(b"partial")
        os.kill(os.getpid(), signal.SIGSEGV)
    if mode == "sleep":
        time.sleep(60)
    sys.exit(3)
""")


def _load_build():
    spec = importlib.util.spec_from_file_location("build_producers_under_test",
                                                  PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def build():
    return _load_build()


class Fakes:
    def __init__(self, root: Path):
        self.root = root
        self.log = root / "calls.jsonl"
        self.bin = root / "bin"
        self.bin.mkdir()
        for name in ("rllvm", "razm", "clang", "as"):
            self.write(name)

    def write(self, name: str, extra: str = "") -> Path:
        path = self.bin / name
        path.write_text(FAKE.format(python=sys.executable, name=name,
                                    log=str(self.log)) + extra)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        return path

    def calls(self, tool: str | None = None) -> list:
        if not self.log.exists():
            return []
        rows = [json.loads(ln) for ln in self.log.read_text().splitlines()]
        return [r for r in rows if tool is None or r["tool"] == tool]


@pytest.fixture
def fakes(tmp_path, monkeypatch, build):
    import producers
    f = Fakes(tmp_path)
    monkeypatch.setenv("PATH", f"{f.bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("RITZ_RLLVM", str(f.bin / "rllvm"))
    monkeypatch.setenv("RITZ_RAZM", str(f.bin / "razm"))
    for env in ("RITZ_OBJ_PRODUCER", "RITZ_ASM_PRODUCER", "RITZ_CLANG_OBJ_TIMEOUT"):
        monkeypatch.delenv(env, raising=False)
    producers.reset_memo()
    yield f
    producers.reset_memo()


def _ll(tmp_path: Path) -> tuple[Path, Path]:
    ll = tmp_path / "m.ll"
    ll.write_text("; module\n")
    return ll, tmp_path / "m.o"


# --- routing: compile_ll_to_obj ------------------------------------------------

def test_rllvm_exit_0_uses_its_object(build, fakes, tmp_path):
    ll, obj = _ll(tmp_path)
    assert build.compile_ll_to_obj(ll, obj, ll, PIC) is None
    assert obj.read_text() == "obj by rllvm"
    assert [c["args"] for c in fakes.calls()] == [[*PIC, str(ll), "-o", str(obj)]]


def test_rllvm_exit_2_falls_back_to_clang_with_same_flags(build, fakes, tmp_path,
                                                          monkeypatch, capsys):
    monkeypatch.setenv("FAKE_RLLVM_MODE", "unsupported")
    ll, obj = _ll(tmp_path)
    assert build.compile_ll_to_obj(ll, obj, ll, PIC) is None
    assert obj.read_text() == "obj by clang"
    assert [c["tool"] for c in fakes.calls()] == ["rllvm", "clang"]
    assert fakes.calls("clang")[0]["args"] == [*PIC, str(ll), "-o", str(obj)]
    notice = [ln for ln in capsys.readouterr().err.splitlines() if "m.ll" in ln]
    assert len(notice) == 1, "the fallback is one line"
    assert "type 'metadata'" in notice[0] and "clang" in notice[0]


@pytest.mark.parametrize("mode, status", [
    ("fail", "exit status 1"),
    ("segv", "killed by signal 11"),
])
def test_rllvm_failure_fails_the_build_without_fallback(build, fakes, tmp_path,
                                                        monkeypatch, mode, status):
    monkeypatch.setenv("FAKE_RLLVM_MODE", mode)
    ll, obj = _ll(tmp_path)
    before = build.CLANG_OBJ_FAILURES
    error = build.compile_ll_to_obj(ll, obj, ll, PIC)
    assert error is not None and "rllvm" in error and status in error
    assert fakes.calls("clang") == [], "exit 1 or a signal never falls back"
    assert not obj.exists(), "a partial object must not survive"
    assert build.CLANG_OBJ_FAILURES == before + 1


def test_rllvm_timeout_fails_the_build(build, fakes, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_RLLVM_MODE", "sleep")
    monkeypatch.setenv("RITZ_CLANG_OBJ_TIMEOUT", "1")
    ll, obj = _ll(tmp_path)
    error = build.compile_ll_to_obj(ll, obj, ll, PIC)
    assert error is not None and "rllvm" in error and "timed out after 1s" in error
    assert fakes.calls("clang") == []


def test_fallback_clang_failure_unlinks_and_names_clang(build, fakes, tmp_path,
                                                        monkeypatch):
    monkeypatch.setenv("FAKE_RLLVM_MODE", "unsupported")
    monkeypatch.setenv("FAKE_CLANG_MODE", "fail")
    ll, obj = _ll(tmp_path)
    error = build.compile_ll_to_obj(ll, obj, ll, PIC)
    assert error is not None and error.startswith("clang -c failed")
    assert not obj.exists()


def test_rllvm_runs_under_the_address_space_cap(build, fakes, tmp_path, monkeypatch):
    monkeypatch.setenv("RITZ_CLANG_OBJ_MEM_MB", "3000")
    ll, obj = _ll(tmp_path)
    assert build.compile_ll_to_obj(ll, obj, ll, PIC) is None
    assert fakes.calls("rllvm")[0]["as_limit"] == 3000 * 1024 * 1024


def test_obj_producer_clang_sends_every_file_to_clang(build, fakes, tmp_path,
                                                      monkeypatch):
    monkeypatch.setenv("RITZ_OBJ_PRODUCER", "clang")
    ll, obj = _ll(tmp_path)
    assert build.compile_ll_to_obj(ll, obj, ll, PIC) is None
    assert [c["tool"] for c in fakes.calls()] == ["clang"]


def test_hosted_O2_stays_on_clang(build, fakes, tmp_path):
    """rllvm is v1 -O0: a hosted suite on its objects ran 20x or more slower
    (rz's call A, AGAST #4808), so the optimized compile is clang's."""
    ll, obj = _ll(tmp_path)
    assert build.compile_ll_to_obj(ll, obj, ll, HOSTED) is None
    assert [c["tool"] for c in fakes.calls()] == ["clang"]
    assert build.compile_ll_to_obj(ll, obj, ll) is None, "OBJ_CLANG_FLAGS, the default"
    assert [c["tool"] for c in fakes.calls()] == ["clang", "clang"]


def test_kernel_model_stays_on_clang(build, fakes, tmp_path):
    """rllvm's v1 frames overflowed harland's 4 KiB kernel stacks (AGAST
    #4808): a kernel-model compile is clang's."""
    ll, obj = _ll(tmp_path)
    assert build.compile_ll_to_obj(ll, obj, ll, KERNEL) is None
    assert [c["tool"] for c in fakes.calls()] == ["clang"]
    import producers
    assert set(producers.obj_identity(KERNEL)) == {"clang"}


def test_uefi_stays_on_clang(build, fakes, tmp_path):
    ll, obj = _ll(tmp_path)
    assert build.compile_ll_to_obj(ll, obj, ll, UEFI) is None
    assert [c["tool"] for c in fakes.calls()] == ["clang"]


def test_unknown_producer_fails_the_build(build, fakes, tmp_path, monkeypatch):
    monkeypatch.setenv("RITZ_OBJ_PRODUCER", "gcc")
    ll, obj = _ll(tmp_path)
    error = build.compile_ll_to_obj(ll, obj, ll, PIC)
    assert error is not None and "RITZ_OBJ_PRODUCER" in error
    assert fakes.calls() == []


# --- assemble_objects ---------------------------------------------------------

def _asm(tmp_path: Path) -> Path:
    s = tmp_path / "boot.s"
    s.write_text(".text\n")
    return s


def test_razm_assembles_from_the_package_dir(build, fakes, tmp_path):
    s = _asm(tmp_path)
    art = tmp_path / "art"
    art.mkdir()
    assert build.assemble_objects([s], tmp_path, art) == [art / "boot.o"]
    (call,) = fakes.calls()
    assert call["tool"] == "razm"
    assert call["args"] == ["--64", "-o", str(art / "boot.o"), str(s)]
    assert call["cwd"] == str(tmp_path), ".incbin paths resolve from the package"


def test_asm_producer_as_switches_back(build, fakes, tmp_path, monkeypatch):
    monkeypatch.setenv("RITZ_ASM_PRODUCER", "as")
    s = _asm(tmp_path)
    assert build.assemble_objects([s], tmp_path, tmp_path) == [tmp_path / "boot.o"]
    assert [c["tool"] for c in fakes.calls()] == ["as"]


def test_razm_failure_has_no_fallback(build, fakes, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_RAZM_MODE", "fail")
    s = _asm(tmp_path)
    assert build.assemble_objects([s], tmp_path, tmp_path) is None
    assert fakes.calls("as") == []
    assert "razm failed for boot.s" in capsys.readouterr().err


# --- ensure_runtime_object: routing and the stamp ------------------------------

def _shim(tmp_path: Path) -> Path:
    ll = tmp_path / "ritz_start.x86_64.ll"
    ll.write_text("; shim\n")
    return ll.with_suffix(".o")


def _stamp(obj: Path) -> Path:
    return obj.with_name(obj.name + ".producer")


def test_shim_goes_to_rllvm_and_is_stamped(build, fakes, tmp_path):
    obj = _shim(tmp_path)
    assert build.ensure_runtime_object(obj) is True
    (call,) = fakes.calls()
    assert call["tool"] == "rllvm" and call["args"][0] == "-c"
    assert obj.read_text() == "obj by rllvm"
    import producers
    assert _stamp(obj).read_text() == producers.stamp_text(producers.obj_identity(["-c"]))
    assert build.ensure_runtime_object(obj) is True
    assert len(fakes.calls()) == 1, "a current, stamped shim is not rebuilt"


def test_shim_exit_2_falls_back_to_clang(build, fakes, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_RLLVM_MODE", "unsupported")
    obj = _shim(tmp_path)
    assert build.ensure_runtime_object(obj) is True
    assert [c["tool"] for c in fakes.calls()] == ["rllvm", "clang"]
    assert obj.read_text() == "obj by clang"


def test_shim_rllvm_failure_publishes_nothing(build, fakes, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_RLLVM_MODE", "fail")
    obj = _shim(tmp_path)
    assert build.ensure_runtime_object(obj) is False
    assert fakes.calls("clang") == []
    assert not obj.exists() and not _stamp(obj).exists()
    assert sorted(p.name for p in tmp_path.iterdir() if p.is_file()) == [
        "calls.jsonl", "ritz_start.x86_64.ll"], "temp file left behind"


@pytest.mark.parametrize("stamp", [None, "{\"clang\": \"another\"}"])
def test_missing_or_different_stamp_rebuilds_the_shim(build, fakes, tmp_path, stamp):
    obj = _shim(tmp_path)
    obj.write_text("old object")
    if stamp is not None:
        _stamp(obj).write_text(stamp)
    assert build.ensure_runtime_object(obj) is True
    assert obj.read_text() == "obj by rllvm"


def test_switching_producer_rebuilds_the_shim(build, fakes, tmp_path, monkeypatch):
    obj = _shim(tmp_path)
    assert build.ensure_runtime_object(obj) is True
    monkeypatch.setenv("RITZ_OBJ_PRODUCER", "clang")
    assert build.ensure_runtime_object(obj) is True
    assert obj.read_text() == "obj by clang"


def test_stamp_is_written_after_the_object_is_replaced(build, fakes, tmp_path,
                                                       monkeypatch):
    obj = _shim(tmp_path)
    _stamp(obj).write_text("stale")
    seen = []
    real = os.replace

    def spy(src, dst):
        if Path(dst) == obj:
            seen.append(_stamp(obj).read_text() if _stamp(obj).exists() else None)
        return real(src, dst)

    monkeypatch.setattr(build.os, "replace", spy)
    assert build.ensure_runtime_object(obj) is True
    assert seen and seen[0] != _stamp(obj).read_text(), (
        "the new stamp existed before the new object: a reader could pair "
        "an old object with a new stamp")


# --- cache identity ------------------------------------------------------------

def test_obj_identity_names_every_producer(fakes):
    import producers
    routed = producers.obj_identity(PIC)
    assert set(routed) == {"rllvm", "razm_lib", "clang"}
    assert routed["rllvm"] == producers.sha256_file(fakes.bin / "rllvm")
    assert set(producers.obj_identity(UEFI)) == {"clang"}
    assert set(producers.obj_identity(HOSTED)) == {"clang"}, "hosted -O2 is clang's"


def test_obj_identity_is_clang_alone_under_the_switch(fakes, monkeypatch):
    import producers
    monkeypatch.setenv("RITZ_OBJ_PRODUCER", "clang")
    assert set(producers.obj_identity(PIC)) == {"clang"}


def test_obj_identity_follows_the_rllvm_binary(fakes):
    import producers
    first = producers.obj_identity(PIC)
    fakes.write("rllvm", extra="# rebuilt\n")
    producers.reset_memo()
    assert producers.obj_identity(PIC) != first


def _module(tmp_path: Path) -> Path:
    src = tmp_path / "pkg" / "m.ritz"
    src.parent.mkdir()
    src.write_text("fn f() -> i32\n    0\n")
    return src


def test_cas_module_key_changes_with_the_producer(build, fakes, tmp_path, monkeypatch):
    import producers
    monkeypatch.setenv("RITZ_NO_KEY_MEMO", "1")
    src = _module(tmp_path)
    cache = build.get_build_cache("ritz0")
    cache.set_import_context(project_root=src.parent)
    kernel = {"freestanding": True, "target_os": "", "clang": PIC[1:]}  # small PIC
    routed = build.cas_module_key(src, cache, "ritz0", kernel)
    hosted = build.cas_module_key(src, cache, "ritz0")
    monkeypatch.setenv("RITZ_OBJ_PRODUCER", "clang")
    assert build.cas_module_key(src, cache, "ritz0", kernel) != routed
    assert build.cas_module_key(src, cache, "ritz0") == hosted, (
        "hosted -O2 is clang's under either setting: its entries stay valid")
    monkeypatch.delenv("RITZ_OBJ_PRODUCER")
    fakes.write("rllvm", extra="# rebuilt\n")
    producers.reset_memo()
    assert build.cas_module_key(src, cache, "ritz0", kernel) != routed


def test_cas_harness_key_names_clang(build, fakes, tmp_path, monkeypatch):
    """The harness object is hosted -O2: clang's, and the key says so."""
    import producers
    src = _module(tmp_path)
    key = build.cas_harness_key(src, [], "ritz0")
    monkeypatch.setenv("RITZ_OBJ_PRODUCER", "clang")
    assert build.cas_harness_key(src, [], "ritz0") == key
    monkeypatch.setattr(producers, "clang_version", lambda: "clang version 0.0")
    assert build.cas_harness_key(src, [], "ritz0") != key


def test_hosted_provenance_records_the_producer(build, fakes, tmp_path, monkeypatch):
    src = _module(tmp_path)
    routed = build.hosted_provenance([src], "ritz0", "H", {"name": "debug"})
    monkeypatch.setenv("RITZ_OBJ_PRODUCER", "clang")
    assert build.hosted_provenance([src], "ritz0", "H", {"name": "debug"}) != routed


def _freestanding_bin(build, tmp_path: Path, asm: Path):
    from manifest import BinaryConfig
    return BinaryConfig(name="k", src_path=tmp_path / "main.ritz", additional_sources=[],
                        freestanding=True, target="x86_64-none-elf", asm_files=[asm])


def test_freestanding_provenance_records_razm_next_to_each_s(build, fakes, tmp_path,
                                                             monkeypatch):
    import producers
    s = _asm(tmp_path)
    config = _freestanding_bin(build, tmp_path, s)
    record = build.freestanding_provenance(config, [], "ritz0", "H", tmp_path)
    (entry,) = record["asm"]
    assert entry[:2] == [str(s.resolve()), producers.sha256_file(s)]
    assert entry[3] == {"razm": producers.sha256_file(fakes.bin / "razm")}
    fakes.write("razm", extra="# rebuilt\n")
    producers.reset_memo()
    assert build.freestanding_provenance(config, [], "ritz0", "H", tmp_path) != record, (
        "a rebuilt razm must relink")
    monkeypatch.setenv("RITZ_ASM_PRODUCER", "as")
    record_as = build.freestanding_provenance(config, [], "ritz0", "H", tmp_path)
    assert "as" in record_as["asm"][0][3]


def test_freestanding_provenance_records_the_obj_producer(build, fakes, tmp_path,
                                                          monkeypatch):
    s = _asm(tmp_path)
    config = _freestanding_bin(build, tmp_path, s)
    routed = build.freestanding_provenance(config, [], "ritz0", "H", tmp_path)
    monkeypatch.setenv("RITZ_OBJ_PRODUCER", "clang")
    assert build.freestanding_provenance(config, [], "ritz0", "H", tmp_path) != routed


# --- the on-demand tool ---------------------------------------------------------

def test_tool_override_must_be_executable(fakes, tmp_path, monkeypatch):
    import producers
    monkeypatch.setenv("RITZ_RLLVM", str(tmp_path / "missing"))
    with pytest.raises(producers.ProducerError, match="RITZ_RLLVM"):
        producers.tool("rllvm")


def test_tool_copy_is_current_only_while_its_sources_are(tmp_path, monkeypatch):
    import producers
    producers.reset_memo()
    monkeypatch.setattr(producers, "tool_compiler", lambda: "ritz0")
    monkeypatch.setattr(producers, "_compiler_hash", lambda compiler: "H")
    src = tmp_path / "a.ritz"
    src.write_text("fn a() -> i32\n    0\n")
    binary = tmp_path / "rllvm"
    binary.write_bytes(b"\x7fELF")
    manifest = binary.with_name("rllvm.manifest.json")

    def record(**over):
        rec = {"compiler": "ritz0", "compiler_hash": "H",
               "binary_sha256": producers.sha256_file(binary),
               "sources": [[str(src), producers.sha256_file(src)]], "runtime": []}
        rec.update(over)
        manifest.write_text(json.dumps(rec))

    record()
    assert producers.is_current(binary)
    record(compiler_hash="other")
    assert not producers.is_current(binary), "a changed ritz0 rebuilds"
    record(compiler="ritz1")
    assert not producers.is_current(binary)
    record()
    src.write_text("fn a() -> i32\n    1\n")
    assert not producers.is_current(binary), "an edited source rebuilds"
    record()
    binary.write_bytes(b"\x7fELF other")
    assert not producers.is_current(binary), "a foreign binary rebuilds"
    manifest.unlink()
    assert not producers.is_current(binary)


@pytest.mark.parametrize("llvmlite, built, want", [
    (True, ["ritz1", "ritz1_selfhosted"], "ritz0"),
    (False, ["ritz1", "ritz1_selfhosted"], "ritz1_selfhosted"),
    (False, ["ritz1"], "ritz1"),
    (False, [], None),
])
def test_tool_compiler_is_ritz0_else_a_built_ritz1(tmp_path, monkeypatch, llvmlite, built,
                                                   want):
    """The builder image ships ritz1_selfhosted and no llvmlite: rllvm and
    razm are built by what can run there."""
    import importlib.util
    import producers
    producers.reset_memo()
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec",
                        lambda name, *a: (real("json") if llvmlite else None)
                        if name == "llvmlite" else real(name, *a))
    monkeypatch.setattr(producers, "ROOT", tmp_path)
    (tmp_path / "ritz1" / "build").mkdir(parents=True)
    for c in built:
        (tmp_path / "ritz1" / "build" / c).write_bytes(b"\x7fELF")
    try:
        if want is None:
            with pytest.raises(producers.ProducerError, match="llvmlite"):
                producers.tool_compiler()
        else:
            assert producers.tool_compiler() == want
    finally:
        producers.reset_memo()
