"""The guarded EC2 boot run, projects/indium/iac/run.sh (AGAST #1849).

run.sh builds the EC2 disk, uploads it as an EBS snapshot, `terraform apply`s
one t3.micro from it (projects/indium/iac/boot-run, local state), polls the
serial console for the rzsh prompt, saves the log under
projects/indium/boot-logs/ and destroys everything it created, always, from
an EXIT trap.

Nothing here talks to AWS. Every run.sh call is `--dry-run`, and PATH starts
with a poisoned `aws` and `terraform` that record any call: the tests fail if
either is ever executed. DRY_* variables steer the canned responses:

* DRY_ACCOUNT    - the account `sts get-caller-identity` reports;
* DRY_FAIL       - a step (snapshot, apply, poll) that fails;
* DRY_CONSOLE    - `prompt` (default), `none` (the prompt never comes) or
                   `panic` (the kernel panics: polling stops at once);
* DRY_STATE_LEFT - non-empty: `terraform state list` still lists a resource.
"""

import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

RITZ0_DIR = Path(__file__).resolve().parents[1]
INDIUM = RITZ0_DIR.parent.parent / "indium"
RUN_SH = INDIUM / "iac" / "run.sh"
BOOT_RUN = INDIUM / "iac" / "boot-run"
TOOLS = INDIUM / "tools"

EXPECTED_ACCOUNT = "412381736149"


# --- harness -------------------------------------------------------------------

@pytest.fixture
def env(tmp_path):
    """A PATH whose aws and terraform record the call and fail."""
    poison = tmp_path / "poison"
    poison.mkdir()
    marker = tmp_path / "touched-aws"
    for tool in ("aws", "terraform"):
        p = poison / tool
        p.write_text(f"#!/bin/sh\necho \"{tool} $*\" >> {marker}\nexit 99\n")
        p.chmod(p.stat().st_mode | stat.S_IXUSR)
    image = tmp_path / "ec2-boot.img"
    image.write_bytes(b"\0" * (1 << 20) + b"KERNEL" + b"\0" * (1 << 20))
    e = {k: v for k, v in os.environ.items() if not k.startswith(("DRY_", "AWS_"))}
    e.update(PATH=f"{poison}:{e['PATH']}", POLL_INTERVAL="0")
    return {"env": e, "marker": marker, "image": image, "logs": tmp_path / "logs"}


def run(env, *args, extra=None, timeout=60):
    e = dict(env["env"], **(extra or {}))
    argv = ["bash", str(RUN_SH), *args]
    p = subprocess.run(argv, env=e, capture_output=True, text=True, timeout=timeout)
    assert not env["marker"].exists(), "touched real AWS: " + env["marker"].read_text()
    return p


def dry(env, *args, extra=None):
    return run(env, "--dry-run", "--no-build", "--image", str(env["image"]),
               "--log-dir", str(env["logs"]), *args, extra=extra)


def steps(out):
    """The `==> step` lines run.sh prints, in order."""
    return re.findall(r"^==> ([\w-]+)", out, re.M)


# --- the files -----------------------------------------------------------------

def test_run_sh_is_executable_bash():
    assert RUN_SH.is_file()
    assert os.access(RUN_SH, os.X_OK), "run.sh is not executable"
    subprocess.run(["bash", "-n", str(RUN_SH)], check=True)


def test_run_sh_shellcheck_clean():
    """AGAST #4359: this used to skip silently wherever shellcheck was not
    installed (the gate host), so a runner-only finding hid for weeks. The
    findings are fixed; where the tool is missing, fail on a CI runner
    instead of skipping, as tools/test_ci_workflows.py does (AGAST #4264)."""
    shellcheck = shutil.which("shellcheck")
    if shellcheck is None:
        if os.environ.get("CI"):
            pytest.fail("shellcheck is not on PATH on a CI runner")
        pytest.skip("shellcheck not on PATH")
    r = subprocess.run([shellcheck, str(RUN_SH)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_boot_run_uses_local_state_not_the_shared_bucket():
    """The S3 key harland-ec2/terraform.tfstate holds a February deployment;
    a destroy against it would delete resources this run never made."""
    tf = "".join(p.read_text() for p in BOOT_RUN.glob("*.tf"))
    assert 'backend "s3"' not in tf
    assert not re.search(r'^\s*(bucket|key)\s*=', tf, re.M), "boot-run must not name a state bucket"


def test_boot_run_only_allows_t3_micro():
    tf = (BOOT_RUN / "variables.tf").read_text()
    block = tf[tf.index('variable "instance_type"'):]
    block = block[:block.index("\n}\n")]
    assert 'default     = "t3.micro"' in block
    assert "validation" in block and '== "t3.micro"' in block


def test_boot_run_ingress_is_only_icmp_from_itself():
    """AGAST #1851: the acceptance boot must be pingable from a peer in the
    same subnet. One self-referencing ICMP rule does that; nothing else is
    exposed, and egress stays open because DHCP and the gateway ping need it.
    """
    tf = (BOOT_RUN / "main.tf").read_text()
    rules = re.findall(r"^\s*ingress\s*\{(.*?)^\s*\}", tf, re.M | re.S)
    assert len(rules) == 1, rules
    assert 'protocol    = "icmp"' in rules[0] or 'protocol = "icmp"' in rules[0]
    assert re.search(r"^\s*self\s*=\s*true", rules[0], re.M)
    assert "cidr_blocks" not in rules[0]
    assert re.search(r"^\s*egress\s*\{.*?0\.0\.0\.0/0", tf, re.M | re.S), \
        "egress is needed for DHCP and the gateway ping"
    assert 'cpu_credits = "standard"' in tf, "t3 unlimited bills surplus credits"
    assert 'instance_initiated_shutdown_behavior = "terminate"' in tf


def test_boot_run_launches_at_most_one_ping_peer_in_the_same_subnet():
    """The peer exists only to ping harland: one t3.micro, the same subnet,
    the same (self-ICMP) security group, and a user-data loop that pings the
    harland private IP until it gets a reply."""
    tf = (BOOT_RUN / "main.tf").read_text()
    assert 'resource "aws_instance" "peer"' in tf
    peer = tf[tf.index('resource "aws_instance" "peer"'):]
    assert "count" in peer[:200] and "var.peer_ping ? 1 : 0" in peer[:300]
    assert "instance_type               = var.instance_type" in tf
    assert "subnet_id                   = local.subnet_id" in tf, \
        "both instances must come up in the same subnet"
    assert "aws_instance.harland.private_ip" in peer
    assert "ping -c 1" in peer
    assert "shutdown -h now" in peer, "the peer must end its own bill"
    assert "vpc_security_group_ids      = [aws_security_group.harland.id]" in peer
    assert 'instance_initiated_shutdown_behavior = "terminate"' in peer


def test_boot_run_outputs_the_peer_for_the_log_header():
    out = (BOOT_RUN / "outputs.tf").read_text()
    assert 'output "peer_instance_id"' in out
    assert 'output "peer_ip"' in out


@pytest.mark.skipif(shutil.which("terraform") is None, reason="terraform not installed")
def test_boot_run_terraform_fmt_clean():
    subprocess.run(["terraform", "fmt", "-check", "-recursive", str(BOOT_RUN)], check=True)


# --- argument handling -----------------------------------------------------------

def test_help(env):
    p = run(env, "--help")
    assert p.returncode == 0
    assert "--dry-run" in p.stdout and "--poll-timeout" in p.stdout


@pytest.mark.parametrize("args", [
    ["--bogus"],
    ["--poll-timeout"],
    ["--poll-timeout", "0"],
    ["--poll-timeout", "abc"],
    ["--poll-timeout", "721"],
    ["--image"],
    ["stray"],
])
def test_bad_arguments_exit_2_before_anything_runs(env, args):
    p = run(env, "--dry-run", *args)
    assert p.returncode == 2, p.stdout + p.stderr
    assert steps(p.stdout) == []


def test_missing_image_with_no_build_is_an_error(env, tmp_path):
    p = run(env, "--dry-run", "--no-build", "--image", str(tmp_path / "nope.img"))
    assert p.returncode == 2
    assert "nope.img" in p.stderr


# --- the happy path ------------------------------------------------------------------

def test_dry_run_steps_in_order_and_log_saved(env):
    p = dry(env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert steps(p.stdout) == [
        "account", "build", "init", "snapshot", "apply", "poll",
        "save-log", "terminate", "destroy", "verify-state", "delete-snapshot", "summary",
    ]
    logs = list(env["logs"].iterdir())
    assert len(logs) == 1
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}-[0-9a-f]{7,40}\.txt", logs[0].name), logs[0].name
    text = logs[0].read_text()
    assert "rzsh> " in text
    assert "t3.micro" in text and "us-west-2" in text, "log header names the instance"
    assert "reached rzsh" in p.stdout


def test_dry_run_reports_instance_seconds_and_cost(env):
    p = dry(env)
    assert re.search(r"billed seconds: \d+", p.stdout)
    assert re.search(r"cost: \$\d+\.\d{4}", p.stdout)


def test_terminate_requested_before_terraform_destroy(env):
    """A halted guest took 4m23s to finish terminating in the first live run.
    Billing stops at shutting-down, so run.sh asks for termination directly
    and stops the instance-time clock there, before terraform waits it out."""
    p = dry(env)
    err = p.stderr
    term = err.index("DRY aws ec2 terminate-instances --instance-ids i-dry")
    assert term < err.index("DRY terraform destroy")


def test_kernel_panic_stops_polling_at_once(env):
    p = dry(env, "--poll-timeout", "600", extra={"DRY_CONSOLE": "panic"})
    assert p.returncode == 4, p.stdout + p.stderr
    assert "kernel panic" in p.stdout
    assert p.stderr.count("get-console-output") == 1, "polled again after the panic"
    log = next(env["logs"].iterdir()).read_text()
    assert "# result: kernel panic" in log


def test_build_runs_make_ec2_disk_unless_no_build(env):
    p = run(env, "--dry-run", "--image", str(env["image"]), "--log-dir", str(env["logs"]))
    assert p.returncode == 0, p.stdout + p.stderr
    assert "DRY make -C" in p.stdout and "ec2-disk" in p.stdout


# --- the guards ------------------------------------------------------------------------

def test_wrong_account_stops_before_anything_is_created(env):
    p = dry(env, extra={"DRY_ACCOUNT": "111111111111"})
    assert p.returncode == 3, p.stdout + p.stderr
    assert "412381736149" in p.stderr
    assert steps(p.stdout) == ["account", "summary"]
    assert "terraform apply" not in p.stdout + p.stderr
    assert not env["logs"].exists() or not list(env["logs"].iterdir())


@pytest.mark.parametrize("step", ["snapshot", "apply", "poll"])
def test_failure_still_destroys_and_deletes_snapshot(env, step):
    p = dry(env, extra={"DRY_FAIL": step})
    assert p.returncode != 0
    done = steps(p.stdout)
    assert done[-4:] == ["destroy", "verify-state", "delete-snapshot", "summary"], done
    assert "DRY terraform destroy" in p.stdout + p.stderr


def test_no_prompt_times_out_saves_log_and_destroys(env):
    p = dry(env, "--poll-timeout", "1", extra={"DRY_CONSOLE": "none"})
    assert p.returncode == 4, p.stdout + p.stderr
    assert "no rzsh prompt" in p.stdout
    assert "save-log" in steps(p.stdout) and "destroy" in steps(p.stdout)
    assert len(list(env["logs"].iterdir())) == 1


def test_leftover_state_is_reported_as_a_leak(env):
    p = dry(env, extra={"DRY_STATE_LEFT": "1"})
    assert p.returncode == 5, p.stdout + p.stderr
    assert "LEAK" in p.stderr


def test_sigterm_mid_poll_still_destroys(env):
    e = dict(env["env"], DRY_CONSOLE="none", POLL_INTERVAL="0.2")
    argv = ["bash", str(RUN_SH), "--dry-run", "--no-build", "--image", str(env["image"]),
            "--log-dir", str(env["logs"]), "--poll-timeout", "60"]
    proc = subprocess.Popen(argv, env=e, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out = []
    deadline = time.time() + 30
    while time.time() < deadline:
        line = proc.stdout.readline()
        out.append(line)
        if line.startswith("==> poll"):
            break
    time.sleep(0.5)
    proc.send_signal(signal.SIGTERM)
    rest, _ = proc.communicate(timeout=30)
    text = "".join(out) + rest
    assert proc.returncode != 0
    assert "==> destroy" in text and "==> verify-state" in text, text
    assert "result: interrupted" in text
    assert not env["marker"].exists()


# --- the helpers ---------------------------------------------------------------------------

sys.path.insert(0, str(TOOLS))


def test_ebs_blocks_skip_zero_blocks_and_checksum():
    import base64
    import hashlib

    import ebs_snapshot

    bs = ebs_snapshot.BLOCK
    data = b"\0" * bs + b"x" * 10 + b"\0" * (bs - 10) + b"\0" * bs + b"tail"
    blocks = list(ebs_snapshot.changed_blocks(data))
    assert [i for i, _, _ in blocks] == [1, 3]
    for _, chunk, digest in blocks:
        assert len(chunk) == bs, "the last block is zero-padded to a full block"
        assert digest == base64.b64encode(hashlib.sha256(chunk).digest()).decode()


def test_ebs_volume_size_rounds_up_to_gib():
    import ebs_snapshot

    assert ebs_snapshot.volume_gib(1) == 1
    assert ebs_snapshot.volume_gib(128 << 20) == 1
    assert ebs_snapshot.volume_gib((1 << 30) + 1) == 2


def test_ebs_upload_call_sequence(tmp_path, monkeypatch):
    """The CLI calls upload makes, with a fake _aws: --block-data is a bare
    path (the CLI rejects fileb:// for this streaming blob; the first live run
    died on it), and complete-snapshot counts exactly the blocks sent."""
    import json

    import ebs_snapshot

    calls = []

    def fake(region, *args):
        calls.append(args)
        if args[1] == "put-snapshot-block":
            path = args[args.index("--block-data") + 1]
            assert not path.startswith("fileb://")
            assert Path(path).stat().st_size == ebs_snapshot.BLOCK
        return json.dumps({"SnapshotId": "snap-x"}) if args[1] == "start-snapshot" else ""

    monkeypatch.setattr(ebs_snapshot, "_aws", fake)
    img = tmp_path / "d.img"
    img.write_bytes(b"a" + bytes(ebs_snapshot.BLOCK * 3) + b"b")
    assert ebs_snapshot.upload(img, "us-west-2", ["RunId=r1"], "d") == "snap-x"
    names = [c[1] for c in calls]
    assert names[0] == "start-snapshot" and names.count("put-snapshot-block") == 2
    assert names[-2:] == ["complete-snapshot", "wait"]
    assert calls[-2][calls[-2].index("--changed-blocks-count") + 1] == "2"
    assert "Key=RunId,Value=r1" in calls[0]


def test_mkec2disk_lays_out_the_esp(tmp_path, monkeypatch):
    # AGAST #4359: the whole ESP is built in Python, so this proves the same
    # layout with the tools absent and present. The empty PATH makes that
    # explicit: the old build called `mmd`/`mcopy` unconditionally, so this
    # test passed in the gate (mtools installed) and failed on a runner.
    sys.path.insert(0, str(INDIUM.parent / "harland" / "inventory"))
    import esp_image
    import mkec2disk

    (tmp_path / "no-tools").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "no-tools"))

    efi, kernel, initrd = (tmp_path / n for n in ("BOOTX64.EFI", "kernel.elf", "initramfs.tar"))
    efi.write_bytes(b"MZ" + b"e" * 3000)
    kernel.write_bytes(b"\x7fELF" + b"k" * 70000)
    initrd.write_bytes(b"t" * 5000)
    out = tmp_path / "ec2-boot.img"
    mkec2disk.build(out, efi, kernel, initrd, size_mib=64)
    assert out.stat().st_size == 64 << 20
    files = {k.lower(): v for k, v in esp_image.read_files(out).items()}
    assert files["efi/boot/bootx64.efi"] == efi.read_bytes()
    assert files["harland/kernel.elf"] == kernel.read_bytes()
    assert files["harland/initramfs.tar"] == initrd.read_bytes()
    assert b"BOOTX64.EFI" in files["startup.nsh"]
    # AGAST #1851: the EC2 image runs the NIC self-tests (ENA, DHCP), and
    # only the peer-ping build adds the responder window.
    assert files["harland/net-selftest"] == b""
    assert "harland/net-responder" not in files


def test_mkec2disk_can_ask_for_the_peer_ping_window(tmp_path):
    """--net-responder adds the second boot marker; the default image does
    not, so an ordinary EC2 boot never waits for a peer that is not there."""
    sys.path.insert(0, str(INDIUM.parent / "harland" / "inventory"))
    import esp_image
    import mkec2disk

    efi, kernel, initrd = (tmp_path / n for n in ("BOOTX64.EFI", "kernel.elf", "initramfs.tar"))
    efi.write_bytes(b"MZ")
    kernel.write_bytes(b"\x7fELF")
    initrd.write_bytes(b"t")
    out = tmp_path / "ec2-boot.img"
    mkec2disk.build(out, efi, kernel, initrd, size_mib=64, net_responder=True)
    files = {k.lower(): v for k, v in esp_image.read_files(out).items()}
    assert files["harland/net-selftest"] == b""
    assert files["harland/net-responder"] == b""


def test_apply_asks_for_the_ping_peer_by_default(env):
    # Without --no-build: the dry run prints the make command it would run.
    p = run(env, "--dry-run", "--image", str(env["image"]), "--log-dir", str(env["logs"]))
    assert p.returncode == 0, p.stdout + p.stderr
    assert "peer_ping=true" in p.stderr
    assert "EC2_NET_RESPONDER=1" in p.stdout


def test_no_peer_flag_leaves_the_peer_out(env):
    p = run(env, "--dry-run", "--image", str(env["image"]), "--log-dir", str(env["logs"]),
            "--no-peer")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "peer_ping=false" in p.stderr
    assert "EC2_NET_RESPONDER=0" in p.stdout
    text = next(env["logs"].iterdir()).read_text()
    assert "# peer: none" in text


def test_log_header_names_the_peer_for_correlation(env):
    p = dry(env)
    assert p.returncode == 0, p.stdout + p.stderr
    text = next(env["logs"].iterdir()).read_text()
    assert "# peer: i-peer-dry 172.31.32.10" in text


def test_two_instances_are_billed_when_the_peer_runs(env):
    p = dry(env)
    assert re.search(r"billed seconds: \d+ x 2 instances", p.stdout), p.stdout


def test_a_committed_nitro_boot_log_exists():
    """#1849's artefact: a serial log from a real Nitro boot, with the header
    run.sh writes and the kernel banner. Partial boots count (see #4334)."""
    logs = sorted((INDIUM / "boot-logs").glob("*.txt"))
    assert logs, "no boot log committed under projects/indium/boot-logs"
    text = logs[-1].read_text(errors="replace")
    assert text.startswith("# harland boot on EC2 Nitro (AGAST #1849)")
    assert re.search(r"^# instance: i-[0-9a-f]+ t3\.micro us-west-2", text, re.M)
    assert "Harland kernel starting..." in text


def test_the_1851_acceptance_log_records_dhcp_and_an_answered_peer_ping():
    """AGAST #1851's acceptance, in the committed artefact: a VPC DHCP lease,
    an echo request from the peer instance, harland's reply, and the peer's
    own console confirming it got the reply."""
    log = INDIUM / "boot-logs" / "2026-11-20-d6937a69d5a3.txt"
    text = log.read_text(errors="replace")
    assert re.search(r"^# peer: i-[0-9a-f]+ 172\.31\.", text, re.M)
    assert re.search(r"\[dhcp\] ACK: 172\.31\.", text)
    assert re.search(r"\[icmp\] Echo request from 172\.31\.", text)
    assert re.search(r"\[icmp\] Sent reply to 172\.31\.", text)
    assert re.search(r"\[net\] peer ping: requests=[1-9]\d* replies=[1-9]\d*", text)
    assert "PEER: got a ping reply from 172.31." in text
