"""Regression tests for AGAST #1301 — ritz1 must fail loudly on unparseable input.

Before this fix, ritz1's generated parser recovered from an item it could not
parse by skipping forward to the next anchor token, clearing the error, and
reporting "progress" to the enclosing `item*` loop.  Nothing recorded the drop:
the compiler emitted IR for the surviving items and exited 0.  A function that
failed to parse simply vanished — surfacing much later as an undefined symbol
at link time, or, if nothing referenced it, as a silently wrong binary with no
diagnostic at all.

The contract these tests pin down:

  1. unparseable input  -> non-zero exit
  2. the diagnostic names file, line, column and the offending construct
  3. no output artifact is written when a top-level item was dropped
  4. valid input still compiles (the check must not fire on good code)

Note on test inputs: `Vec<Vec<i64>>` was the construct that exposed the bug,
but ritz1 nested-generic parity is AGAST #1300 and will make it parse.  These
tests therefore use input that is unparseable by construction (`fn ***(` and
raw punctuation salad), so they keep testing the recovery path after #1300.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    """Path to the ritz1 binary, building it if it is not present.

    Deliberately does NOT skip when the binary is missing: a skipped test is
    indistinguishable from a passing one in aggregate output, and "reported
    success while asserting nothing" is the exact failure family #1301 is about.
    """
    if not RITZ1_BIN.exists():
        env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
        proc = subprocess.run(
            ["make", "-C", "ritz1", "ritz1"],
            cwd=RITZ_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        if proc.returncode != 0 or not RITZ1_BIN.exists():
            pytest.fail(
                "could not build ritz1 for the parse-error regression tests:\n"
                f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
            )
    return RITZ1_BIN


def _compile(ritz1: Path, tmp_path: Path, source: str, name: str = "case"):
    src = tmp_path / f"{name}.ritz"
    src.write_text(source)
    out = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [str(ritz1), str(src), "-o", str(out)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc, src, out


# An item that no future grammar extension is going to start accepting.
BROKEN_ITEM = "fn ***(\n"


@pytest.mark.integration
def test_unparseable_item_exits_nonzero(ritz1_bin, tmp_path):
    proc, _src, _out = _compile(
        ritz1_bin,
        tmp_path,
        "fn good_before() -> i32\n    1\n\n" + BROKEN_ITEM + "\nfn main() -> i32\n    0\n",
    )
    assert proc.returncode != 0, (
        "ritz1 exited 0 on input it could not parse (AGAST #1301)\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )


@pytest.mark.integration
def test_unparseable_item_reports_file_and_location(ritz1_bin, tmp_path):
    proc, src, _out = _compile(
        ritz1_bin,
        tmp_path,
        "fn good_before() -> i32\n    1\n\n" + BROKEN_ITEM + "\nfn main() -> i32\n    0\n",
    )
    err = proc.stderr + proc.stdout
    assert str(src) in err, f"diagnostic does not name the source file:\n{err}"
    # The broken item starts on line 4, column 1.
    assert f"{src}:4:1" in err, f"diagnostic lacks file:line:col for the bad item:\n{err}"
    assert "cannot parse item" in err, f"diagnostic does not say what went wrong:\n{err}"
    assert "fn" in err, f"diagnostic does not name the failing construct:\n{err}"


@pytest.mark.integration
def test_unparseable_item_writes_no_artifact(ritz1_bin, tmp_path):
    proc, _src, out = _compile(ritz1_bin, tmp_path, "fn ok() -> i32\n    0\n\n" + BROKEN_ITEM)
    assert proc.returncode != 0
    assert not out.exists(), (
        "ritz1 emitted an output artifact despite dropping a top-level item — "
        "this is the link-time-mystery path from AGAST #1301"
    )


@pytest.mark.integration
def test_trailing_garbage_is_not_silently_ignored(ritz1_bin, tmp_path):
    """Junk after the last item used to be swallowed whole, exit 0."""
    proc, _src, out = _compile(
        ritz1_bin, tmp_path, "fn ok() -> i32\n    0\n\n@@@ !!! not ritz at all\n"
    )
    assert proc.returncode != 0, f"trailing garbage accepted:\n{proc.stderr}"
    assert not out.exists()


@pytest.mark.integration
def test_valid_module_still_compiles(ritz1_bin, tmp_path):
    """The EOF/dropped-item check must not fire on well-formed input."""
    proc, _src, out = _compile(
        ritz1_bin,
        tmp_path,
        "struct Point\n    x: i32\n    y: i32\n\n"
        "const K: i32 = 3\n\n"
        "fn add(a: i32, b: i32) -> i32\n    a + b\n\n"
        "fn main() -> i32\n    add(K, 4) - 7\n",
    )
    assert proc.returncode == 0, f"valid module rejected:\n{proc.stderr}"
    assert out.exists()
    ir = out.read_text()
    for sym in ("@add", "@main"):
        assert sym in ir, f"{sym} missing from emitted IR:\n{ir[:2000]}"
