"""AGAST #4216: `ritz1 -- <input.ritz>` writes its IR under $TMPDIR, per pid.

The `--` form (end-of-flags, for test harnesses) used to write a fixed
/tmp/ritz1_dashdash_out.ll.  Up to two gates and six rooms share one host's
/tmp, so two concurrent runs wrote the same file and one could read the
other's IR.  The output is now $TMPDIR/ritz1_dashdash_<pid>.ll ($TMPDIR
defaulting to /tmp), unique per process and inside the caller's own scratch.

Two cases: two concurrent runs in one fresh TMPDIR must each leave their own
IR there (with the fixed name, the TMPDIR stays empty); and no ritz1 source
names a fixed /tmp path again.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ1_SRC = Path(__file__).resolve().parent.parent / "ritz1" / "src"

# The one /tmp literal ritz1 may hold: the sig cache's last-resort root
# (fn_cache.ritz, after $RITZ_CACHE_DIR, $XDG_CACHE_HOME and $HOME), a
# content-addressed cache shared on purpose.
ALLOWED_TMP = {("fn_cache.ritz", '"/tmp/ritz-cache"')}
# A name under /tmp; bare "/tmp" is a directory default, not a file name.
TMP_LITERAL = re.compile(r'c?"/tmp/[^"]*"')


@pytest.mark.unit
def test_ritz1_src_names_no_fixed_tmp_path():
    hits = []
    for f in sorted(RITZ1_SRC.glob("*.ritz")):
        for n, line in enumerate(f.read_text().splitlines(), 1):
            code = line.split("#", 1)[0]
            for m in TMP_LITERAL.finditer(code):
                if (f.name, m.group(0).lstrip("c")) not in ALLOWED_TMP:
                    hits.append(f"{f.name}:{n}: {m.group(0)}")
    assert hits == [], f"a fixed /tmp name races a concurrent run (AGAST #4216): {hits}"


@pytest.mark.integration
def test_concurrent_dashdash_runs_write_own_ir_under_tmpdir(ritz1_bin, tmp_path):
    scratch = tmp_path / "tmpdir"
    scratch.mkdir()
    env = {**os.environ, "TMPDIR": str(scratch)}
    procs = []
    for name in ("alpha_4216", "beta_4216"):
        src = tmp_path / f"{name}.ritz"
        src.write_text(f"pub fn {name}() -> i32\n    return 7\n\npub fn main() -> i32\n    return {name}()\n")
        procs.append(subprocess.Popen(
            [str(ritz1_bin), "--", str(src)], env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ))
    for p in procs:
        out, err = p.communicate(timeout=50)
        assert p.returncode == 0, err

    outs = sorted(scratch.glob("ritz1_dashdash_*.ll"))
    assert [o.name for o in outs] == sorted(f"ritz1_dashdash_{p.pid}.ll" for p in procs)
    irs = [o.read_text() for o in outs]
    assert sum("alpha_4216" in ir for ir in irs) == 1
    assert sum("beta_4216" in ir for ir in irs) == 1
