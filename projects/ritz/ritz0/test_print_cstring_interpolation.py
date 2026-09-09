#!/usr/bin/env python3
"""`print(c"...{x}...")` must be rejected, not silently printed verbatim.

AGAST #1374, decided 2026-09-09 (option (b)).

    let x: i64 = 21
    print("bare: {x}\\n")     ->  bare: 21     correct
    print(c"cstr: {x}\\n")    ->  cstr: {x}    WRONG

The c-string form compiles clean, exits 0, and produces wrong output with no
diagnostic of any kind. `examples/tier5_async/72_raii` shipped exactly this:
once its two other bugs were fixed it built, linked and ran with exit 0 while
printing `counter_new: id={id}, start={start}` against an expected_output of
`counter_new: id=1, start=0`. An exit-0 program emitting placeholder text is
precisely what a "does it build?" gate calls success.

== WHY WE REJECT RATHER THAN INTERPOLATE ==

The obvious fix -- make c"..." interpolate too, for consistency -- was
measured and REJECTED. The corpus has 48 c"..." literals containing a
`{ident}` placeholder (ritz 34, nexus 12, sage 1, valet 1). Number passed to
print: ZERO. All 48 rely on `{...}` staying opaque.

The worst case is ritz1's own emitter, which emits LLVM inline-asm constraint
strings like `"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"`. Interpolating
those corrupts every syscall the self-hosted compiler emits.

That is why `test_cstring_with_braces_outside_print_still_compiles` uses
ritz1's actual constraint string as its fixture: the self-hosting hazard is
guarded explicitly, rather than by luck. It is the load-bearing test in this
file -- without it, "reject every c-string containing braces" would pass.

The check therefore lives in the `print` builtin's lowering, NOT in the lexer
or the parser. A lexer/parser-level fix would hit all 48 sites.
"""

import os
import subprocess
import sys
from pathlib import Path

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"


def _compile(tmp_path, name, source):
    src = tmp_path / name
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )


CSTR_INTERP = """\
fn main() -> i32
    let x: i64 = 21
    print(c"cstr var: {x}\\n")
    return 0
"""

PLAIN_INTERP = """\
fn main() -> i32
    let x: i64 = 21
    print("bare var: {x}\\n")
    return 0
"""

# ritz1's real inline-asm constraint string. `{rax}` and `{rdi}` are LLVM
# register constraints, not placeholders. This MUST keep compiling.
RITZ1_ASM_CONSTRAINT = """\
fn emit(s: *u8) -> i64
    return 0

fn main() -> i32
    let c: *u8 = c"={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"
    emit(c)
    return 0
"""

CSTR_NO_BRACES = """\
fn main() -> i32
    print(c"plain cstring, no placeholders\\n")
    return 0
"""


def test_print_cstring_with_placeholder_is_rejected(tmp_path):
    """The defect itself: this must not compile silently."""
    r = _compile(tmp_path, "interp.ritz", CSTR_INTERP)
    assert r.returncode != 0, (
        "print(c\"...{x}...\") compiled cleanly -- it prints the placeholder "
        "verbatim, which is silently wrong output"
    )


def test_rejection_names_a_source_location(tmp_path):
    """An anonymous error is not much better than none. Cf. #1366."""
    r = _compile(tmp_path, "interp.ritz", CSTR_INTERP)
    out = r.stdout + r.stderr
    assert "interp.ritz:3" in out, (
        f"diagnostic did not name file:line of the print call:\n{out}"
    )


def test_rejection_is_not_a_python_traceback(tmp_path):
    """It is a user error, so it must be reported as one."""
    r = _compile(tmp_path, "interp.ritz", CSTR_INTERP)
    out = r.stdout + r.stderr
    assert "Traceback (most recent call last)" not in out, (
        f"user error surfaced as a Python traceback:\n{out}"
    )


def test_rejection_suggests_the_plain_string_form(tmp_path):
    """The fix is one character. Say so, rather than making them guess."""
    r = _compile(tmp_path, "interp.ritz", CSTR_INTERP)
    out = r.stdout + r.stderr
    assert 'interpolat' in out.lower(), (
        f"diagnostic does not explain that c-strings do not interpolate:\n{out}"
    )


# ---------------------------------------------------------------------------
# Controls. Without these, "reject anything with a brace" passes.
# ---------------------------------------------------------------------------

def test_plain_string_interpolation_still_compiles(tmp_path):
    """The working form must be untouched."""
    r = _compile(tmp_path, "plain.ritz", PLAIN_INTERP)
    assert r.returncode == 0, (
        f"print(\"...{{x}}...\") stopped compiling:\n{r.stdout}\n{r.stderr}"
    )


def test_cstring_with_braces_outside_print_still_compiles(tmp_path):
    """LOAD-BEARING: ritz1's asm constraints must not be collateral damage.

    If this ever fails, the check has leaked out of the print builtin and the
    self-hosted compiler is about to emit corrupt syscalls.
    """
    r = _compile(tmp_path, "asm.ritz", RITZ1_ASM_CONSTRAINT)
    assert r.returncode == 0, (
        "a c-string containing {rax} that is NOT passed to print was "
        f"rejected -- this breaks ritz1's emitter:\n{r.stdout}\n{r.stderr}"
    )


def test_print_cstring_without_placeholders_still_compiles(tmp_path):
    """print(c"...") is idiomatic and overwhelmingly common. Do not break it."""
    r = _compile(tmp_path, "nobrace.ritz", CSTR_NO_BRACES)
    assert r.returncode == 0, (
        f"print(c\"...\") with no placeholders was rejected:\n{r.stdout}\n{r.stderr}"
    )
