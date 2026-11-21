"""Harland waits on a calibrated TSC, not on pause counts (AGAST #4181).

apic.ritz's delay_us counted `us * 100` pause instructions ("assumes ~1GHz
CPU"), so the AP INIT/SIPI waits and the AP startup timeout were as long as the
CPU was slow; postinit, the ACPI shutdown retry and the ENA driver spun
`while delay < N` loops of no particular length.

Now arch/x86_64/tsc.ritz calibrates the TSC once (CPUID 0x15 when it names
the crystal, else PIT channel 2 over a ~10 ms gate, else CPUID 0x16, else a
deliberately high guess), logs the frequency, and exposes tsc_hz(), time_ns(),
delay_us() and TSC deadlines; every wait is a deadline on it. The arithmetic
lives in arch/x86_64/tsc_calc.ritz (no imports, no hardware), which the
behaviour test compiles into a host program; its exit code names the failed
claim. The source-level tests pin that the pause-count loops are gone.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
KERNEL_SRC = RITZ_ROOT.parent / "harland" / "kernel" / "src"
TSC_CALC = KERNEL_SRC / "arch" / "x86_64" / "tsc_calc.ritz"
TSC = KERNEL_SRC / "arch" / "x86_64" / "tsc.ritz"
APIC = KERNEL_SRC / "arch" / "x86_64" / "apic.ritz"
ENA = KERNEL_SRC / "drivers" / "ena" / "device.ritz"
MAIN = KERNEL_SRC / "main.ritz"

PROGRAM = """\
import arch.x86_64.tsc_calc

fn main() -> i32
    # PIT input clock and the ~10 ms gate
    if PIT_HZ != 1193182 or PIT_GATE_TICKS != 11931
        return 1
    # 3 GHz TSC over a 10 ms gate: 29_999_... cycles in 11931 PIT ticks
    let hz: u64 = tsc_hz_from_pit(30000000 * 11931 / 11932, 11931)
    if hz < 2990000000 or hz > 3010000000
        return 2
    if tsc_hz_from_pit(12345, 0) != 0
        return 3
    # any gate length: 9M cycles over 3579 ticks (~3 ms) is ~3 GHz
    if tsc_hz_from_pit(9000000, 3579) != 3000457669
        return 20
    # CPUID 0x15: crystal * EBX / EAX; any zero field means "not enumerated"
    if tsc_hz_from_cpuid15(2, 216, 24000000) != 2592000000
        return 4
    if tsc_hz_from_cpuid15(0, 216, 24000000) != 0 or tsc_hz_from_cpuid15(2, 0, 24000000) != 0 or tsc_hz_from_cpuid15(2, 216, 0) != 0
        return 5
    # CPUID 0x16: base MHz in EAX[15:0]
    if tsc_hz_from_cpuid16(0x0BB8) != 3000000000 or tsc_hz_from_cpuid16(0xFFFF0000) != 0
        return 6
    # plausible: 100 MHz .. 20 GHz
    if tsc_hz_plausible(99999999) or not tsc_hz_plausible(100000000) or not tsc_hz_plausible(20000000000) or tsc_hz_plausible(20000000001)
        return 7
    # us -> cycles, exact for non-round frequencies
    if tsc_cycles_for_us(3000000000, 10) != 30000 or tsc_cycles_for_us(2592000000, 1000000) != 2592000000
        return 8
    # the sub-MHz part of the frequency counts (2.5 MHz, not 2 MHz)
    if tsc_cycles_for_us(2500000, 1000000) != 2500000 or tsc_cycles_for_us(2592500000, 2) != 5185
        return 21
    if tsc_cycles_for_us(1500000, 1) != 1 or tsc_cycles_for_us(1999999, 1) != 1 or tsc_cycles_for_us(3000000000, 0) != 0
        return 9
    # an hour at 5 GHz doesn't overflow
    if tsc_cycles_for_us(5000000000, 3600000000) != 18000000000000
        return 10
    # cycles -> ns
    if tsc_cycles_to_ns(3000000000, 3000000000) != 1000000000 or tsc_cycles_to_ns(3000000000, 3) != 1
        return 11
    if tsc_cycles_to_ns(2592000000, 2592000000 * 100 + 1296000000) != 100500000000
        return 12
    if tsc_cycles_to_ns(0, 12345) != 0
        return 13
    # deadlines: now + cycles, saturating; passed once now reaches it
    let dl: u64 = tsc_deadline(1000, 3000000000, 10)
    if dl != 31000
        return 14
    if tsc_deadline_passed(30999, dl) or not tsc_deadline_passed(31000, dl) or not tsc_deadline_passed(40000, dl)
        return 15
    if tsc_deadline(0xFFFFFFFFFFFFFF00, 3000000000, 1000) != 0xFFFFFFFFFFFFFFFF
        return 16
    if tsc_deadline_passed(0xFFFFFFFFFFFFFFFE, 0xFFFFFFFFFFFFFFFF)
        return 17
    # a zero-length wait has already passed
    if not tsc_deadline_passed(500, tsc_deadline(500, 3000000000, 0))
        return 18
    # the fallback guess errs long: above any real TSC we'd boot on
    if TSC_FALLBACK_HZ < 5000000000 or not tsc_hz_plausible(TSC_FALLBACK_HZ)
        return 19
    0
"""

CLAIMS = {1: "PIT constants", 2: "PIT gate -> ~3 GHz", 3: "zero PIT ticks -> 0",
          4: "CPUID 0x15 crystal ratio", 5: "CPUID 0x15 zero fields -> 0", 6: "CPUID 0x16 base MHz",
          7: "plausibility bounds", 8: "us -> cycles", 9: "us -> cycles for tiny frequencies",
          10: "us -> cycles doesn't overflow", 11: "cycles -> ns", 12: "cycles -> ns non-round",
          13: "cycles -> ns with hz 0", 14: "deadline = now + cycles", 15: "deadline passed at/after",
          16: "deadline saturates", 17: "near-max deadline not passed early", 18: "zero wait passed",
          19: "fallback errs long", 20: "PIT any gate length", 21: "us -> cycles keeps sub-MHz"}


@pytest.mark.integration
def test_tsc_deadline_arithmetic(tmp_path):
    tree = tmp_path / "tree" / "arch" / "x86_64"
    tree.mkdir(parents=True)
    (tree / "tsc_calc.ritz").write_text(TSC_CALC.read_text())
    (tmp_path / "t.ritz").write_text(PROGRAM)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    objs = []
    for src, name, extra in [(tmp_path / "t.ritz", "t", ()),
                             (tree / "tsc_calc.ritz", "tsc_calc", ("--no-runtime",))]:
        ll = tmp_path / f"{name}.ll"
        proc = run_ritz0([str(src), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
        assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
        objs.append(str(ll))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe), "-nostdlib", "-no-pie"],
                          capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-3000:]
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert rc == 0, f"exit {rc}: {CLAIMS.get(rc, 'crash')}"


# --- source level: no pause-count waits left ------------------------------------

def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


@pytest.mark.unit
def test_no_pause_count_delays_in_kernel():
    bad = []
    for path in sorted(KERNEL_SRC.rglob("*.ritz")):
        code = _code(path)
        for pat in (r"while delay <", r"\bus \* 100\b"):
            if re.search(pat, code):
                bad.append(f"{path.relative_to(KERNEL_SRC)}: {pat}")
    assert not bad, bad


@pytest.mark.unit
def test_tsc_module_is_the_one_timer():
    assert TSC_CALC.exists() and TSC.exists()
    calc = _code(TSC_CALC)
    assert not re.search(r"^import\b", calc, re.M), "tsc_calc.ritz must stay import-free (host-compiled)"
    tsc = _code(TSC)
    for fn in ("tsc_calibrate", "tsc_hz", "time_ns", "delay_us", "deadline_after_us", "deadline_passed"):
        assert re.search(rf"^pub fn {fn}\(", tsc, re.M), f"tsc.ritz doesn't export {fn}"
    cal = _body(tsc, "tsc_calibrate")
    # CPUID 0x15 first, then PIT channel 2 (ports 0x42/0x43/0x61), then 0x16
    assert cal.index("0x15") < cal.index("pit_calibrate()") < cal.index("0x16"), cal
    pit = _body(tsc, "pit_measure")
    for name, port in (("PIT_CH2_DATA", "0x42"), ("PIT_COMMAND", "0x43"), ("PORT_61", "0x61")):
        assert re.search(rf"^const {name}: u16 = {port}$", tsc, re.M), f"{name} is not port {port}"
        assert name in pit, f"pit_measure doesn't use {name}"
    assert "0x80000007" in tsc, "invariant TSC (CPUID 0x80000007 EDX[8]) not checked"
    # main calibrates early (and logs it) before APs are started
    main = _code(MAIN)
    assert main.index("tsc_calibrate()") < main.index("ap_boot_all()")


@pytest.mark.unit
def test_apic_waits_are_deadlines():
    code = _code(APIC)
    assert not re.search(r"^(?:pub\s+)?fn delay_us\(", code, re.M), "apic.ritz still has its own delay_us"
    assert re.search(r"^import arch\.x86_64\.tsc\b", code, re.M)
    boot_one = _body(code, "ap_boot_one")
    assert "deadline_after_us(" in boot_one and "deadline_passed(" in boot_one, boot_one
    assert not re.search(r"timeout = timeout - 1", boot_one), "AP startup timeout still counts iterations"


@pytest.mark.unit
def test_ena_waits_are_deadlines():
    code = _code(ENA)
    for fn in ("ena_wait_for_reset_state", "ena_wait_for_ready", "ena_admin_wait_completion"):
        body = _body(code, fn)
        assert "deadline_after_us(" in body and "deadline_passed(" in body, f"{fn} not on a deadline"
        assert not re.search(r"while (?:timeout|iterations|i) < \d", body), f"{fn} still counts iterations"
