"""AGAST #1835: one module pipeline for every target, hosted and freestanding.

`compile_freestanding_binary` used to keep its own copy of compile_binary's
discover -> emit -> verify -> object loop. The copy drifted:

* it ran `clang -c` itself instead of `compile_ll_to_obj`, so a freestanding
  object compile had no timeout and no address-space cap (AGAST #1731);
* it returned on the first clang failure, so a kernel with N modules clang
  rejects showed one of them (contrary to AGAST #1286).

Both now go through `compile_modules` with a `Target` value. These tests
stub ritz0 (the compiler) and run the real clang on whatever IR the stub
writes. Source discovery still goes through ritz0/list_deps.py.
"""

import importlib
import importlib.util
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

cas = importlib.import_module("cas")

needs_clang = pytest.mark.skipif(
    subprocess.run(["sh", "-c", "command -v clang"], capture_output=True).returncode != 0,
    reason="clang not on PATH")

GOOD_IR = "define void @_start() {\n  ret void\n}\n"
BAD_IR = "this is not LLVM IR\n"

# Writes `ir` to the `-o` path, for any module.
STUB = textwrap.dedent(
    """\
    #!{python}
    import sys
    args = sys.argv[1:]
    with open(args[args.index("-o") + 1], "w") as f:
        f.write({ir!r})
    """
)


@pytest.fixture(autouse=True)
def private_store(tmp_path, monkeypatch):
    monkeypatch.setenv(cas.CAS_DIR_ENV, str(tmp_path / "cas"))
    monkeypatch.delenv(cas.STATS_LOG_ENV, raising=False)
    monkeypatch.setenv("RITZ_PATH", str(PKG_DIR))


@pytest.fixture
def buildpy(tmp_path):
    spec = importlib.util.spec_from_file_location(
        f"ritz_buildpy_1835_{tmp_path.name}", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.get_build_cache("ritz0")._cache_dir = tmp_path / ".ritz-cache"
    return mod


def _stub_ritz0(tmp_path, monkeypatch, buildpy, ir):
    stub = tmp_path / "ritz0_stub.py"
    stub.write_text(STUB.format(python=sys.executable, ir=ir))
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(buildpy, "RITZ0", stub)


@pytest.fixture
def obj_calls(buildpy, monkeypatch):
    """Every compile_ll_to_obj call, as (source name, flags)."""
    calls = []
    real = buildpy.compile_ll_to_obj

    def recording(ll_path, obj_path, src, flags=None):
        calls.append((Path(src).name, flags))
        return real(ll_path, obj_path, src, flags) if flags is not None \
            else real(ll_path, obj_path, src)

    monkeypatch.setattr(buildpy, "compile_ll_to_obj", recording)
    return calls


def _two_module_kernel(tmp_path):
    pkg = tmp_path / "fs_pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "kern.ritz").write_text("import helper\n\nfn _start()\n    return\n")
    (pkg / "src" / "helper.ritz").write_text("fn h() -> i32\n    1\n")
    return pkg


def _build_kernel(buildpy, pkg, use_cache=False):
    bin_config = buildpy.BinaryConfig(
        name="kern", src_path=pkg / "src" / "kern.ritz", additional_sources=[],
        freestanding=True, target="x86_64-unknown-none", no_red_zone=True)
    out = pkg / "build"
    out.mkdir(exist_ok=True)
    return buildpy.compile_freestanding_binary(
        bin_config, out, pkg, use_cache=use_cache, source_roots=["src"])


@pytest.mark.unit
@needs_clang
def test_freestanding_objects_go_through_the_bounded_compile(
        buildpy, obj_calls, tmp_path, monkeypatch):
    _stub_ritz0(tmp_path, monkeypatch, buildpy, GOOD_IR)
    _build_kernel(buildpy, _two_module_kernel(tmp_path))  # link outcome irrelevant
    assert sorted(name for name, _ in obj_calls) == ["helper.ritz", "kern.ritz"], \
        "a freestanding module was compiled to an object outside compile_ll_to_obj"
    for _, flags in obj_calls:
        # The target's own object flags, not the hosted -O2 -fPIC set.
        assert "--target=x86_64-unknown-none" in flags
        assert "-mno-red-zone" in flags
        assert "-O2" not in flags


@pytest.mark.unit
@needs_clang
def test_freestanding_reports_every_module_clang_rejects(
        buildpy, tmp_path, monkeypatch, capsys):
    _stub_ritz0(tmp_path, monkeypatch, buildpy, BAD_IR)
    assert _build_kernel(buildpy, _two_module_kernel(tmp_path)) is None
    err = capsys.readouterr().err
    assert "helper.ritz" in err and "kern.ritz" in err, \
        "the build stopped at the first clang failure (AGAST #1286)"
    assert buildpy.CLANG_OBJ_FAILURES == 2


@pytest.mark.unit
@needs_clang
def test_freestanding_object_compile_honours_the_memory_cap(
        buildpy, tmp_path, monkeypatch, capsys):
    # The AGAST #1731 bounds now apply to freestanding objects too. A
    # 1 MiB address-space cap kills clang before it starts, and the message
    # names the bound.
    _stub_ritz0(tmp_path, monkeypatch, buildpy, GOOD_IR)
    monkeypatch.setenv(buildpy.CLANG_OBJ_MEM_ENV, "1")  # 1 MiB: clang cannot start
    assert _build_kernel(buildpy, _two_module_kernel(tmp_path)) is None
    assert "address space 1 MiB" in capsys.readouterr().err


@pytest.mark.unit
@needs_clang
def test_hosted_objects_keep_the_hosted_flags(buildpy, obj_calls, tmp_path, monkeypatch):
    _stub_ritz0(tmp_path, monkeypatch, buildpy, GOOD_IR)
    pkg = _two_module_kernel(tmp_path)
    buildpy.compile_binary("kern", pkg / "src" / "kern.ritz", tmp_path, use_cache=False,
                           pkg_dir=pkg, source_roots=["src"])
    assert len(obj_calls) == 2
    for _, flags in obj_calls:
        assert flags in (None, buildpy.OBJ_CLANG_FLAGS)
