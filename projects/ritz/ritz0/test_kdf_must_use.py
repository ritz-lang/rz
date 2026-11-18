"""AGAST #3613: the HKDF / TLS 1.3 key-schedule fns are `[[must_use]]`.

Each returns Ok/Err (or 0/-1) and leaves its output untouched on refusal
(#2579, #2763), so a caller that drops the result goes on with an
uninitialised key.  #2763 and #3612 made every library caller check it;
`[[must_use]]` (LANGUAGE_SPEC §17.8) keeps a new discard from compiling.
The compiler side of the rule is test_must_use.py's; this table only pins
the attribute on each fn.
"""

import re
from pathlib import Path

import pytest

PROJECTS = Path(__file__).resolve().parents[2]

# (source file under projects/, fn) for every fn the ticket names.
MUST_USE = [
    ("cryptosec/lib/hkdf.ritz", "hkdf_expand"),
    ("cryptosec/lib/hkdf.ritz", "hkdf_sha256"),
    ("cryptosec/lib/hkdf.ritz", "hkdf_expand_str"),
    ("cryptosec/lib/tls13_kdf.ritz", "hkdf_expand_label"),
    ("cryptosec/lib/tls13_kdf.ritz", "derive_secret"),
    ("cryptosec/lib/tls13_kdf.ritz", "tls13_derive_traffic_keys"),
    ("cryptosec/lib/tls13_kdf.ritz", "tls13_key_schedule_derive_handshake"),
    ("cryptosec/lib/tls13_kdf.ritz", "tls13_key_schedule_derive_application"),
    ("cryptosec/lib/tls13_kdf.ritz", "tls13_key_schedule_derive_handshake_keys"),
    ("cryptosec/lib/tls13_kdf.ritz", "tls13_key_schedule_derive_application_keys"),
    ("cryptosec/lib/tls13_handshake.ritz", "finished_compute"),
    ("mausoleum/lib/session_kdf.ritz", "session_kdf_derive"),
]


@pytest.mark.unit
def test_kdf_fns_are_must_use():
    missing = []
    for rel, name in MUST_USE:
        lines = (PROJECTS / rel).read_text().splitlines()
        idx = [i for i, ln in enumerate(lines) if re.match(rf"pub fn {name}\(", ln)]
        assert len(idx) == 1, f"{rel}: expected one `pub fn {name}`, found {len(idx)}"
        if lines[idx[0] - 1].strip() != "[[must_use]]":
            missing.append(f"{rel}: {name}")
    assert not missing, "not [[must_use]]: " + ", ".join(missing)
