"""harland's test_tier1_boot.sh `kvm` mode skips where KVM can't run (#4612).

The gate on omegalisk (WSL2) has a /dev/kvm that exists but belongs to an
unmapped nobody:nogroup inside its user namespace: `[ -r ]`/`[ -w ]` pass for
root there, open() fails, and the KVM boot printed nothing and FAILed.  The
mode must SKIP (exit 0, saying why) when the device is absent, can't be
opened read-write, or QEMU's KVM accelerator won't start, and still FAIL a
boot that goes wrong under working KVM.

KVM_DEV stands in for /dev/kvm: a directory is a device that exists but no
one (root included) can open read-write; /dev/null opens fine.  The fake
qemu-system-x86_64 answers the script's `-machine none` accelerator probe
(passing or failing per FAKE_KVM_PROBE) and dies at once on a real boot.
"""

import importlib.util
import os
import subprocess
import textwrap
from pathlib import Path

import pytest

# The sock-path test's stand-in checkout, loaded by path: a bare
# `from test_tier1_boot_sock_path import` reads as an undeclared third-party
# module to tools/test_tools_requirements.py.
_spec = importlib.util.spec_from_file_location(
    "_tier1_sock_path", Path(__file__).with_name("test_tier1_boot_sock_path.py"))
_sock_path = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sock_path)
_tree = _sock_path._tree

FAKE_QEMU = textwrap.dedent("""\
    #!/bin/sh
    case " $* " in
    *" -machine none "*)
        cat >/dev/null
        if [ "$FAKE_KVM_PROBE" = fail ]; then
            echo "Could not access KVM kernel module: Permission denied" >&2
            echo "qemu-system-x86_64: -accel kvm: failed to initialize kvm: Permission denied" >&2
            exit 1
        fi
        exit 0 ;;
    esac
    echo "boot: fake QEMU died before the guest printed anything" >&2
    exit 1
    """)

# (KVM_DEV, FAKE_KVM_PROBE, exit status, stdout fragment)
CASES = [
    ("absent", "ok", 0, "is absent; the KVM boot did not run"),
    ("dir", "ok", 0, "can't be opened read-write; the KVM boot did not run"),
    ("/dev/null", "fail", 0, "QEMU's KVM accelerator failed to start (Could not access KVM"),
    ("/dev/null", "ok", 1, "FAIL (kvm): no ring-0 (CS 8) verdict"),
]


@pytest.mark.integration
@pytest.mark.parametrize("dev,probe,rc,line", CASES, ids=["absent", "unopenable", "accel-fails", "boot-fails"])
def test_tier1_kvm_mode_skips_only_when_kvm_cannot_run(tmp_path, dev, probe, rc, line):
    script = _tree(tmp_path / "repo")
    bins = tmp_path / "bin"
    bins.mkdir()
    (bins / "qemu-system-x86_64").write_text(FAKE_QEMU)
    (bins / "qemu-img").write_text('#!/bin/sh\nexec touch "$(eval echo \\${$#})"\n')
    for b in bins.iterdir():
        b.chmod(0o755)
    ovmf = tmp_path / "OVMF_CODE.fd"
    ovmf.touch()
    kvm_dev = {"absent": str(tmp_path / "no-kvm"), "dir": str(tmp_path)}.get(dev, dev)
    env = dict(os.environ, PATH=f"{bins}:{os.environ['PATH']}", SKIP_BUILD="1",
               OVMF_CODE=str(ovmf), BOOT_TIMEOUT="20", BOOT_STALL="2", POWEROFF_WAIT="2",
               KVM_DEV=kvm_dev, FAKE_KVM_PROBE=probe)
    r = subprocess.run(["bash", str(script), "kvm"], capture_output=True, text=True,
                       timeout=90, env=env)
    out = r.stdout + r.stderr
    assert r.returncode == rc, out
    assert line in r.stdout, out
    if rc == 0:
        assert "FAIL" not in out, out
