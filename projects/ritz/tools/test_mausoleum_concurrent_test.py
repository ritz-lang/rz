"""mausoleum's concurrent_test.sh must finish on a shared, AppArmor-confined host
(AGAST #3202).

On starbux, Test 2 held its silent connection with `nc 127.0.0.1 "$port" &`.
nc runs there under the AppArmor profile `nc.openbsd//&unprivileged_userns`,
which refuses signals from the test: `kill "$nc_pid"` failed with
`Permission denied` (hidden by `2>/dev/null`), and the following
`wait "$nc_pid"` blocked forever.  Three rules, one per part of the fix:

  * no nc/ncat/netcat/socat: a connection is held by a bash `/dev/tcp` fd on a
    process the script started and can signal (`sleep N <>/dev/tcp/...`).
  * no `exec ... 2>...` outside a `{ ...; }` group: on a bare `exec` with no
    command the redirections apply to the shell itself, so wait_for_port's
    `exec 6<>/dev/tcp/... 2>/dev/null` silenced every later stderr line of
    the script.
  * no fixed default PORT_BASE: two rooms on one host running it on the same
    default ports collide, so with PORT_BASE unset the script probes for a
    free range.

These are static checks: the script needs a built mausoleum, which the gate
does not build.  The runtime proof (hang before, 14/14 after) is in #3202.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "projects" / "mausoleum" / "tools" / "concurrent_test.sh"


def _code_lines(text: str):
    """[(line_no, code)] with shell comments removed (`#` at start or after a blank)."""
    return [
        (n, re.split(r"(?:^|\s)#", line, maxsplit=1)[0])
        for n, line in enumerate(text.splitlines(), 1)
    ]


# A netcat-family command word: at line start or after an operator / `(` / `$(`.
NETCAT = re.compile(r"(?:^|[;&|(]|\$\()\s*(?:nc|ncat|netcat|socat)(?:\.\w+)?\b")
# `exec` whose redirections include stderr, before any `;` or `}` closes a group.
PERSISTENT_STDERR = re.compile(r"\bexec\b[^;}]*\s2>")
# PORT_BASE defaulting to a literal number.
FIXED_PORT_BASE = re.compile(r"\bPORT_BASE:-\d")


def netcat_uses(text: str):
    return [(n, c.strip()) for n, c in _code_lines(text) if NETCAT.search(c)]


def persistent_stderr_execs(text: str):
    return [(n, c.strip()) for n, c in _code_lines(text) if PERSISTENT_STDERR.search(c)]


def fixed_port_base(text: str):
    return [(n, c.strip()) for n, c in _code_lines(text) if FIXED_PORT_BASE.search(c)]


# --- the detectors are red-capable --------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("src, detector, flagged", [
    ('nc 127.0.0.1 "$port" < /dev/null > /dev/null 2>&1 &', netcat_uses, True),
    ('x=$(nc -q1 localhost $P)', netcat_uses, True),
    ('echo hi | ncat localhost 1', netcat_uses, True),
    ('sleep 600 <>/dev/tcp/127.0.0.1/"$port" &', netcat_uses, False),
    ('# a silent nc used to hold the slot', netcat_uses, False),
    ('local nc_pid=$!', netcat_uses, False),
    ('if exec 6<>/dev/tcp/127.0.0.1/"$port" 2>/dev/null; then', persistent_stderr_execs, True),
    ('exec 2>/dev/null', persistent_stderr_execs, True),
    ('if { exec 6<>/dev/tcp/127.0.0.1/"$port"; } 2>/dev/null; then', persistent_stderr_execs, False),
    ('exec 6>&-', persistent_stderr_execs, False),
    ('PORT_BASE="${PORT_BASE:-17800}"', fixed_port_base, True),
    ('PORT_BASE="${PORT_BASE:-$(pick_free_port_base)}"', fixed_port_base, False),
])
def test_detector(src, detector, flagged):
    assert bool(detector(src)) is flagged


# --- the rules, over the script ---------------------------------------------


@pytest.mark.unit
def test_no_netcat_holds_a_connection():
    hits = netcat_uses(SCRIPT.read_text())
    assert hits == [], (
        "AppArmor confines nc on starbux and refuses the test's kill, so "
        "`wait` hangs: hold the connection with `sleep N <>/dev/tcp/...` "
        f"(AGAST #3202): {hits}"
    )


@pytest.mark.unit
def test_no_exec_redirects_the_scripts_own_stderr():
    hits = persistent_stderr_execs(SCRIPT.read_text())
    assert hits == [], (
        "a bare `exec` with `2>` redirects the script's stderr for good: "
        f"wrap it, `{{ exec ...; }} 2>/dev/null` (AGAST #3202): {hits}"
    )


@pytest.mark.unit
def test_port_base_is_probed_not_fixed():
    text = SCRIPT.read_text()
    assert fixed_port_base(text) == [], (
        "two rooms on one host collide on a fixed default PORT_BASE: probe "
        "for a free range when it is unset (AGAST #3202)"
    )
    assert re.search(r"^\s*(?:local\s+)?PORT_BASE=\"?\$\{PORT_BASE:-\$\(", text, re.M), (
        "PORT_BASE must default to a probed free range"
    )
