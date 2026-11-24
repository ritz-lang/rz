"""One ENA admin round trip: submit, wait, read the completion (AGAST #4579).

drivers/ena/device.ritz open-coded the admin round trip five times:

    cmd_id = ena_admin_submit_cmd(dev, @cmd as *EnaAdminAqEntry)
    result = ena_admin_wait_completion(dev, cmd_id)
    if result != 0 ...
    prev_head = ena_get_prev_cq_head(aq)
    resp = ena_admin_cq_entry_addr(aq, prev_head) as *<Response>

Now ena_admin_exec(dev, cmd, out_cq_entry) does all of it. It returns 0, the
negated completion status, or -1 on timeout. On success it hands back the
completion entry for callers that read response fields.

Two tests:

  * The host-compiled one builds the real driver against the fake ENA from
    test_harland_ena_tx_buffers.py and checks the success, error-status and
    timeout paths. It uses the fake's admin settings (reply status, hold).
  * The source test checks that only the helper calls ena_admin_submit_cmd,
    ena_admin_wait_completion or ena_get_prev_cq_head, so the copies can't
    come back.

ENA exists only on Nitro (#1851). The QEMU boot gate never reaches this
driver, so this test is its only regular runtime check.
"""

import re
from pathlib import Path

import pytest

from test_harland_ena_tx_buffers import KERNEL_SRC, _run


DEVICE = KERNEL_SRC / "drivers" / "ena" / "device.ritz"

# Exit code -> the claim that failed.
CHECKS = {
    1: "ena_init failed against the emulated device",
    2: "a command the device completed with ENA_ADMIN_SUCCESS did not return 0",
    3: "a successful command did not hand back its completion entry",
    4: "the completion entry handed back is not this command's (wrong command_id)",
    5: "the completion entry handed back does not carry the response fields",
    6: "a NULL out_cq_entry was not accepted",
    10: "a completion with status 5 did not return -5",
    11: "a failed command handed back a completion entry",
    12: "after a failed command, the next command did not succeed: the CQ head "
    "was not advanced past the failed completion",
    20: "a command the device never answers did not time out with -1",
    21: "a timed-out command handed back a completion entry",
}

PROGRAM = """\
import drivers.ena.device { EnaDevice, ena_init, ena_get_device, ena_admin_exec }
import drivers.ena.admin {
    EnaAdminAqEntry, EnaAdminAcqEntry, EnaAdminGetFeatureCmd, EnaAdminMaxQueuesFeature,
    ENA_ADMIN_GET_FEATURE, ENA_ADMIN_MAX_QUEUES_NUM
}
import fakeena { fake_admin_status, fake_admin_hold }

var g_cmd: EnaAdminGetFeatureCmd

fn build_get_max_queues() -> *EnaAdminAqEntry
    var i: u64 = 0
    while i < 64
        *((@g_cmd as u64 + i) as *u8) = 0
        i = i + 1
    g_cmd.common_desc.opcode = ENA_ADMIN_GET_FEATURE
    g_cmd.feature_id = ENA_ADMIN_MAX_QUEUES_NUM
    @g_cmd as *EnaAdminAqEntry

fn main() -> i32
    if ena_init() != 0
        return 1
    let dev: *EnaDevice = ena_get_device()
    let none: *EnaAdminAcqEntry = 0 as *EnaAdminAcqEntry

    # Success: 0, and the entry is this command's completion with its fields.
    var cqe: *EnaAdminAcqEntry = none
    var cmd: *EnaAdminAqEntry = build_get_max_queues()
    if ena_admin_exec(dev, cmd, @cqe) != 0
        return 2
    if cqe == none
        return 3
    if (*cqe).common_desc.command_id != (*cmd).common_desc.command_id
        return 4
    if (*(cqe as *EnaAdminMaxQueuesFeature)).max_sq_num != 8
        return 5

    # Callers that read no response fields pass NULL.
    if ena_admin_exec(dev, build_get_max_queues(), 0 as **EnaAdminAcqEntry) != 0
        return 6

    # Error status: the negated status, no entry, and the queue stays in step.
    fake_admin_status(5)
    cqe = none
    if ena_admin_exec(dev, build_get_max_queues(), @cqe) != -5
        return 10
    if cqe != none
        return 11
    fake_admin_status(0)
    if ena_admin_exec(dev, build_get_max_queues(), @cqe) != 0
        return 12

    # Timeout: the device never answers.
    fake_admin_hold(true)
    cqe = none
    if ena_admin_exec(dev, build_get_max_queues(), @cqe) != -1
        return 20
    if cqe != none
        return 21
    0
"""


@pytest.mark.integration
def test_ena_admin_exec_success_error_and_timeout(tmp_path):
    rc = _run(tmp_path, PROGRAM)
    assert rc == 0, f"check {rc}: {CHECKS.get(rc, 'crashed or unknown exit code')}"


# --- source ratchet -------------------------------------------------------------

FN_HEADER = re.compile(r"^(?:pub )?fn (\w+)\(", re.M)
ROUND_TRIP = ("ena_admin_submit_cmd", "ena_admin_wait_completion", "ena_get_prev_cq_head")


def _callers(text, name):
    """Names of the functions whose bodies call `name`, once per call."""
    headers = list(FN_HEADER.finditer(text))
    out = []
    for i, h in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[h.end() : end]
        body = "\n".join(line.split("#", 1)[0] for line in body.splitlines())
        out += [h.group(1)] * len(re.findall(rf"\b{name}\(", body))
    return out


@pytest.mark.unit
@pytest.mark.parametrize("name", ROUND_TRIP)
def test_only_ena_admin_exec_runs_the_admin_round_trip(name):
    callers = _callers(DEVICE.read_text(), name)
    assert callers == ["ena_admin_exec"], (
        f"{name} is called from {callers}; an admin command goes through "
        "ena_admin_exec (AGAST #4579), which submits, waits and reads the "
        "completion in one place"
    )
