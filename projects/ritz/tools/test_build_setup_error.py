"""A missing toolchain binary is a SETUP error, not a build regression (AGAST #2141).

The room gate runs CI's build-all job (`rz build --all`). On a machine without
LLVM's COFF linker, harland's UEFI loader (bootx64) cannot link, and the build
failed with exit 1 -- indistinguishable from a compiler change that broke
harland. Either reading is wrong: calling it a pass hides real breakage on the
day lld-link IS present, and calling it a regression blames the commit for the
machine.

So build.py reports a third outcome:

  * exit 0 -- every declared target built
  * exit 1 -- at least one target failed for a reason that is the code's fault
  * exit 3 (EXIT_SETUP) -- targets failed, and EVERY failure was a missing tool

A mixed failure (one target missing lld-link, another failing to compile) is
exit 1: the setup miss must never mask a real one.

The compiler is a stub, so these run with no ritz0: it writes a trivial IR
module, or fails when the source file is named `broken.ritz`.
"""

import importlib.util
import stat
import sys
import textwrap
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]

STUB = textwrap.dedent(
    """\
    #!{python}
    import sys
    args = sys.argv[1:]
    if any(a.endswith("broken.ritz") for a in args):
        sys.stderr.write("stub compiler: deliberate failure\\n")
        sys.exit(1)
    out = args[args.index("-o") + 1]
    with open(out, "w") as f:
        f.write("define void @efi_main() {{\\n  ret void\\n}}\\n")
    """
)


@pytest.fixture
def buildpy(request, tmp_path, monkeypatch):
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_2141", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    stub = tmp_path / "ritz0_stub.py"
    stub.write_text(STUB.format(python=sys.executable))
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(mod, "RITZ0", stub)

    # The machine under test has no lld-link, whatever this one has.
    real = mod.find_llvm_tool
    monkeypatch.setattr(
        mod, "find_llvm_tool",
        lambda name: "lld-link-absent-2141" if name == "lld-link" else real(name))
    return mod


def _make_pkg(tmp_path, bins):
    """bins: [(name, src_stem, target)] -- each a freestanding [[bin]]."""
    pkg = tmp_path / "pkg_2141"
    (pkg / "src").mkdir(parents=True)
    toml = '[package]\nname = "pkg_2141"\nversion = "0.1.0"\n'
    for name, stem, target in bins:
        toml += (f'\n[[bin]]\nname = "{name}"\npath = "src/{stem}.ritz"\n'
                 f'target = "{target}"\nfreestanding = true\n')
        (pkg / "src" / f"{stem}.ritz").write_text("fn efi_main()\n    return\n")
    (pkg / "ritz.toml").write_text(toml)
    return pkg


def _build(buildpy, monkeypatch, pkg):
    monkeypatch.setattr(sys, "argv", ["build.py", "build", str(pkg), "--no-cache"])
    return buildpy.main() or 0


def _text(capsys):
    out = capsys.readouterr()
    return out.out + out.err


@pytest.mark.unit
def test_missing_lld_link_exits_with_the_setup_code(buildpy, tmp_path, monkeypatch, capsys):
    pkg = _make_pkg(tmp_path, [("bootx64", "boot", "x86_64-unknown-uefi")])
    rc = _build(buildpy, monkeypatch, pkg)
    text = _text(capsys)
    assert rc == buildpy.EXIT_SETUP == 3, text
    assert "lld-link not found" in text
    # Named as the environment's fault, with the target it cost.
    assert "SETUP ERROR" in text and "bootx64" in text


@pytest.mark.unit
def test_setup_miss_does_not_mask_a_real_failure(buildpy, tmp_path, monkeypatch, capsys):
    pkg = _make_pkg(tmp_path, [("bootx64", "boot", "x86_64-unknown-uefi"),
                               ("kern", "broken", "x86_64-unknown-uefi")])
    rc = _build(buildpy, monkeypatch, pkg)
    text = _text(capsys)
    assert rc == 1, text
    assert "deliberate failure" in text


@pytest.mark.unit
def test_package_result_separates_setup_failures(buildpy):
    r = buildpy.PackageBuildResult(built=[], failed=["a"], skipped=[], setup_failed=["a"])
    assert not r.ok and r.setup_only
    r = buildpy.PackageBuildResult(built=[], failed=["a", "b"], skipped=[], setup_failed=["a"])
    assert not r.ok and not r.setup_only
    r = buildpy.PackageBuildResult(built=[], failed=[], skipped=[])
    assert r.ok and not r.setup_only
