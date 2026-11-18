#!/usr/bin/env python3
"""Compile every fenced ``ritz`` example in the documentation.

AGAST #1311.  The language documentation linked from the top-level README
had no mechanism that could fail.  It sat at "Version 0.2.0 (February
2026)" through the entire RERITZ migration, teaching syntax the compiler
rejects with a *bespoke migration diagnostic* -- we knew the syntax had
changed, updated the error message, and left the document that taught it
alone.  That is the same defect family as a hollow regression baseline: a
thing that reports success while asserting nothing.

This script is the mechanism that can fail.  It extracts every fenced
```ritz block from the documents listed on the command line, compiles each
one with the reference compiler (ritz0), and exits non-zero if any block
does not do what its fence says it does.  A block that compiles also has
its emitted IR parsed and verified (``verify_ir``, AGAST #1358): ritz0
exiting 0 over invalid IR is a failure, not a pass.

Usage:
    python3 tools/check_doc_examples.py DOC.md [DOC.md ...]
    python3 tools/check_doc_examples.py --list DOC.md      # no compiling
    python3 tools/check_doc_examples.py -v DOC.md          # per-block lines
    python3 tools/check_doc_examples.py --compiler ritz1 DOC.md
                        # or ritz1_selfhosted; see COMPILERS, KNOWN_FAILURES

Under ritz1 and ritz1_selfhosted (AGAST #3928) every rule below holds but
one: an ``expect-error`` block must be *refused* with a diagnostic (a crash
is not a refusal), not refused with ritz0's wording, and where the value pins
a ``.ritz:L:C`` position ritz1 must point at the same one.

Exit status: 0 when every block behaves as declared, 1 otherwise.


THE FENCE INFO-STRING
---------------------

A block's fence declares what the block *is*, and the checker holds it to
that declaration.  The first word is always ``ritz`` (so syntax
highlighting keeps working); attributes follow, separated by whitespace or
commas::

    ```ritz                               top-level items; must compile
    ```ritz body                          statements; wrapped, must compile
    ```ritz expect-error="Expected IDENT" must FAIL, with that text in the
                                          diagnostic
    ```ritz no-compile="<reason>"         not compiled; reason mandatory
    ```ritz expect-runtime-error="left:  3"
                                          must COMPILE, then RUN and exit
                                          non-zero with that text on stderr

``body`` exists because much of the prose illustrates a statement or two
rather than a whole program.  Those blocks are wrapped in a ``fn`` and a
trailing ``return 0`` before compiling, so they are still *compiled* --
the fragment-ness is handled by a preamble, not by an exemption.

``expect-error`` is how a document demonstrates a mistake.  Such blocks
are not skipped: they must fail, and they must fail with the diagnostic
the prose claims they produce.  A block that starts compiling because the
compiler grew a feature is a documentation bug, and this reports it.

``expect-runtime-error`` (AGAST #1869) is ``expect-error`` for behaviour
the compiler cannot see: what a failing ``assert`` prints, say.  The block is
top-level items with a ``main``; it is compiled, linked freestanding and
run, and it must exit non-zero with the declared text in its stderr.  In
the value, ``\\n`` is a newline and ``\\\\`` a backslash, so a multi-line
diagnostic can be pinned.

``no-compile`` is the escape hatch, and it is deliberately awkward:

  * the reason is MANDATORY and must be a real sentence (>= 12 chars);
  * every reason is printed in the summary of every run, so the set of
    exemptions is visible rather than accumulating in a file nobody opens;
  * an unlabelled or empty reason is a hard error, not a warning.

An opt-out that is easy and unlabelled becomes the next allowlist nobody
prunes.  We deleted eight such entries two days ago (AGAST #1308); this
one is built to be uncomfortable to add to.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path


# projects/ritz/tools/check_doc_examples.py -> projects/ritz
RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"

# AGAST #3928.  The gate compiled every example with ritz0 alone, so a doc
# example ritz1 refuses (or miscompiles into invalid IR) passed it.  Each
# compiler is checked in its own run (`--compiler`); CI's bootstrap job runs
# all three once ritz1 and ritz1_selfhosted are built.
#
# compiler -> (binary, the make target that builds it).  ritz0 is a script
# run under this interpreter, so it has no binary to be missing.
COMPILERS: dict[str, tuple[Path | None, str | None]] = {
    "ritz0": (None, None),
    "ritz1": (RITZ_ROOT / "ritz1" / "build" / "ritz1", "make -C projects/ritz ritz1-bootstrap"),
    "ritz1_selfhosted": (
        RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted",
        "make -C projects/ritz ritz1-bootstrap",
    ),
}

# ritz0 embeds `_start` in a module that has a `main`; ritz1's emitter is
# never freestanding (build.py: ritz1_compile_cmd), so an
# expect-runtime-error block it compiled is linked with this entry point.
RITZ1_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.ll"

# Doc examples a ritz1-family compiler is KNOWN to get wrong, each naming the
# open ritz1 ticket (under #1828) that tracks the cause.  This is the only way
# to exempt a block from one compiler; `no-compile` exempts it from all three
# and says nothing about ritz1.
#
# Key: (compiler, document file name, block digest).  The digest is
# `Block.digest` -- the first 12 hex of the block's SHA-256, fence attributes
# included -- printed beside every failure.  It is not the line number, so an
# edit elsewhere in the document does not invalidate the entry; an edit to the
# block itself does, which is the point: the edited example has to be checked
# again.  The line in the comment is where the block was when it was listed.
#
# An entry is held to its claim: if the block passes under that compiler, or
# no checked block has that digest, the run fails and names the stale entry.
KNOWN_FAILURES: dict[tuple[str, str, str], str] = {
    # LANGUAGE_SPEC.md:609
    ("ritz1", "LANGUAGE_SPEC.md", "167278a25a58"): "#3935: usize and u64 are different generic args",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "167278a25a58"): "#3935: usize and u64 are different generic args",
    # LANGUAGE_SPEC.md:648
    ("ritz1", "LANGUAGE_SPEC.md", "95abc5851402"): "#3930: `*mut T` doesn't parse",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "95abc5851402"): "#3930: `*mut T` doesn't parse",
    # LANGUAGE_SPEC.md:3332
    ("ritz1", "LANGUAGE_SPEC.md", "81234ed3c9ab"): "#3932: an undeclared field type emits invalid IR",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "81234ed3c9ab"): "#3932: an undeclared field type emits invalid IR",
    # LANGUAGE_SPEC.md:3525
    ("ritz1", "LANGUAGE_SPEC.md", "014099d52fe2"): "#1295: multi-field enum variants",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "014099d52fe2"): "#1295: multi-field enum variants",
    # LANGUAGE_SPEC.md:3667
    ("ritz1", "LANGUAGE_SPEC.md", "419a1826fb7d"): "#1295: multi-field enum variants",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "419a1826fb7d"): "#1295: multi-field enum variants",
    # LANGUAGE_SPEC.md:3692
    ("ritz1", "LANGUAGE_SPEC.md", "a59b32b47b5f"): "#1295: multi-field enum variants",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "a59b32b47b5f"): "#1295: multi-field enum variants",
    # LANGUAGE_SPEC.md:3961
    ("ritz1", "LANGUAGE_SPEC.md", "e774da8b4a14"): "#3309: `Type.m()` on a generic impl isn't instantiated",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "e774da8b4a14"): "#3309: `Type.m()` on a generic impl isn't instantiated",
    # LANGUAGE_SPEC.md:3977
    ("ritz1", "LANGUAGE_SPEC.md", "20aa669fe4ef"): "#3309: `Type.m()` on a generic impl isn't instantiated",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "20aa669fe4ef"): "#3309: `Type.m()` on a generic impl isn't instantiated",
    # LANGUAGE_SPEC.md:4651
    ("ritz1", "LANGUAGE_SPEC.md", "b92c5caa90fc"): "#3473: R57 borrow checks (move while borrowed)",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "b92c5caa90fc"): "#3473: R57 borrow checks (move while borrowed)",
    # LANGUAGE_SPEC.md:4671
    ("ritz1", "LANGUAGE_SPEC.md", "d5e720496ce5"): "#3473: R57 borrow checks (Span view is a borrow)",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "d5e720496ce5"): "#3473: R57 borrow checks (Span view is a borrow)",
    # LANGUAGE_SPEC.md:4803
    ("ritz1", "LANGUAGE_SPEC.md", "c05c5e7b9c6a"): "#3473: R57 borrow checks (return a view of a local)",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "c05c5e7b9c6a"): "#3473: R57 borrow checks (return a view of a local)",
    # LANGUAGE_SPEC.md:6308
    ("ritz1", "LANGUAGE_SPEC.md", "22246d46210c"): "#3933: non-literal print() argument accepted",
    ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "22246d46210c"): "#3933: non-literal print() argument accepted",
    # STDLIB_REFERENCE.md:357
    ("ritz1", "STDLIB_REFERENCE.md", "baa9817ce1f7"): "#3934: `heap <expr>` doesn't parse",
    ("ritz1_selfhosted", "STDLIB_REFERENCE.md", "baa9817ce1f7"): "#3934: `heap <expr>` doesn't parse",
    # STDLIB_REFERENCE.md:455
    ("ritz1", "STDLIB_REFERENCE.md", "c7949d7a5cce"): "#3932: an undeclared field type emits invalid IR",
    ("ritz1_selfhosted", "STDLIB_REFERENCE.md", "c7949d7a5cce"): "#3932: an undeclared field type emits invalid IR",
    # STDLIB_REFERENCE.md:1653
    ("ritz1", "STDLIB_REFERENCE.md", "1ced72f242f7"): "#3932: an undeclared field type emits invalid IR",
    ("ritz1_selfhosted", "STDLIB_REFERENCE.md", "1ced72f242f7"): "#3932: an undeclared field type emits invalid IR",
    # STDLIB_REFERENCE.md:1703
    ("ritz1", "STDLIB_REFERENCE.md", "c53f0f72c88f"): "#3932: an undeclared field type emits invalid IR",
    ("ritz1_selfhosted", "STDLIB_REFERENCE.md", "c53f0f72c88f"): "#3932: an undeclared field type emits invalid IR",
    # STDLIB_REFERENCE.md:2050
    ("ritz1", "STDLIB_REFERENCE.md", "579ac74f08cf"): "#3932: an undeclared field type emits invalid IR",
    ("ritz1_selfhosted", "STDLIB_REFERENCE.md", "579ac74f08cf"): "#3932: an undeclared field type emits invalid IR",
}

TICKET_RE = re.compile(r"(?:AGAST )?#\d+")

# Minimum length of a `no-compile` reason.  Not a real semantic check --
# nothing can stop a determined person writing "because" twice -- but it
# does stop the reflexive `no-compile=""` / `no-compile="fragment"` that
# turns an exemption into a shrug.
MIN_REASON_LEN = 12

FENCE_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<ticks>```+|~~~+)(?P<info>.*)$")

# Attributes are separated by whitespace or commas, but a quoted value may
# contain both, so we lex rather than split.
ATTR_RE = re.compile(
    r"""
    (?P<key>[A-Za-z][A-Za-z0-9_-]*)
    (?: \s* = \s* (?: "(?P<dq>[^"]*)" | '(?P<sq>[^']*)' | (?P<bare>[^\s,]*) ) )?
    """,
    re.VERBOSE,
)


class FenceError(Exception):
    """The fence info-string itself is malformed."""


@dataclass
class Block:
    """One fenced ```ritz block lifted out of a markdown file."""

    doc: Path
    line: int  # 1-based line number of the opening fence
    code: str
    mode: str = "items"  # "items" | "body"
    expect_error: str | None = None
    expect_runtime_error: str | None = None
    no_compile_reason: str | None = None

    info: str = ""  # the fence info-string, attributes included

    @property
    def where(self) -> str:
        return f"{self.doc}:{self.line}"

    @property
    def digest(self) -> str:
        """Stable identity of the block for KNOWN_FAILURES (AGAST #3928)."""
        payload = f"{self.info.strip()}\n{self.code}".encode()
        return hashlib.sha256(payload).hexdigest()[:12]


@dataclass
class Result:
    block: Block
    ok: bool
    detail: str = ""
    skipped: bool = False
    known: str | None = None  # the KNOWN_FAILURES reason, when it applied


@dataclass
class Report:
    results: list[Result] = field(default_factory=list)

    @property
    def failures(self) -> list[Result]:
        return [r for r in self.results if not r.ok]

    @property
    def skips(self) -> list[Result]:
        return [r for r in self.results if r.skipped]

    @property
    def compiled(self) -> list[Result]:
        return [r for r in self.results if r.ok and not r.skipped and not r.known]

    @property
    def known(self) -> list[Result]:
        return [r for r in self.results if r.known]


# ---------------------------------------------------------------------------
# Fence parsing
# ---------------------------------------------------------------------------


def parse_info_string(info: str, where: str) -> dict[str, str | None]:
    """Parse the attributes trailing the ``ritz`` language tag.

    Returns a dict of attribute -> value (None when the attribute was
    written bare).  Raises FenceError for anything we do not recognise --
    a typo'd attribute must not silently degrade into "compile it plainly",
    because that is how ``expect-eror="..."`` would turn an assertion into
    a no-op.
    """
    attrs: dict[str, str | None] = {}
    rest = info.strip()
    # Strip the leading language tag; the caller has already established it.
    rest = rest[len("ritz"):].lstrip(", \t")
    pos = 0
    while pos < len(rest):
        if rest[pos] in " \t,":
            pos += 1
            continue
        m = ATTR_RE.match(rest, pos)
        if not m:
            raise FenceError(f"{where}: cannot parse fence info-string: ```{info.strip()}")
        key = m.group("key")
        value = m.group("dq")
        if value is None:
            value = m.group("sq")
        if value is None:
            value = m.group("bare") or None
        attrs[key] = value
        pos = m.end()
    return attrs


def block_from_fence(doc: Path, line: int, info: str, code: str) -> Block:
    where = f"{doc}:{line}"
    attrs = parse_info_string(info, where)
    block = Block(doc=doc, line=line, code=code, info=info)

    known = {"body", "items", "expect-error", "expect-runtime-error", "no-compile"}
    unknown = sorted(set(attrs) - known)
    if unknown:
        raise FenceError(
            f"{where}: unknown fence attribute(s) {', '.join(unknown)}. "
            f"Known attributes: {', '.join(sorted(known))}."
        )

    if "body" in attrs and "items" in attrs:
        raise FenceError(f"{where}: `body` and `items` are mutually exclusive.")
    if "body" in attrs:
        block.mode = "body"

    if "expect-error" in attrs:
        expected = (attrs["expect-error"] or "").strip()
        if not expected:
            raise FenceError(
                f"{where}: `expect-error` must name the diagnostic, e.g. "
                f'```ritz expect-error="Expected IDENT, got MUT". '
                f"A bare expect-error asserts only that *something* went wrong."
            )
        block.expect_error = expected

    if "expect-runtime-error" in attrs:
        expected = (attrs["expect-runtime-error"] or "").strip()
        if not expected:
            raise FenceError(
                f"{where}: `expect-runtime-error` must name the stderr text, e.g. "
                f'```ritz expect-runtime-error="left:  3\\n  right: 4".'
            )
        if "expect-error" in attrs or "no-compile" in attrs or "body" in attrs:
            raise FenceError(
                f"{where}: `expect-runtime-error` is a whole program that compiles "
                f"and runs; it cannot be combined with `expect-error`, "
                f"`no-compile` or `body`."
            )
        block.expect_runtime_error = _decode_escapes(expected)

    if "no-compile" in attrs:
        reason = (attrs["no-compile"] or "").strip()
        if len(reason) < MIN_REASON_LEN:
            raise FenceError(
                f"{where}: `no-compile` requires a reason of at least "
                f"{MIN_REASON_LEN} characters explaining why this block cannot "
                f'be compiled, e.g. ```ritz no-compile="pseudo-code sketch of a '
                f'not-yet-implemented trait system". Got: {reason!r}'
            )
        block.no_compile_reason = reason

    if block.expect_error and block.no_compile_reason:
        raise FenceError(
            f"{where}: a block cannot be both `expect-error` and `no-compile` "
            f"-- an example that demonstrates an error must assert that it fails."
        )

    return block


def _decode_escapes(text: str) -> str:
    """``\\n`` -> newline and ``\\\\`` -> backslash; nothing else is special."""
    out = []
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in "n\\":
            out.append("\n" if text[i + 1] == "n" else "\\")
            i += 2
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def extract_blocks(doc: Path) -> list[Block]:
    """Lift every fenced ```ritz block out of a markdown document.

    Handles indented fences (inside list items) and longer fence runs, and
    ignores ```ritz-looking text that appears inside a longer outer fence
    -- documentation about this checker necessarily contains examples of
    the fences it checks.
    """
    blocks: list[Block] = []
    lines = doc.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue

        indent, ticks, info = m.group("indent"), m.group("ticks"), m.group("info")
        open_line = i + 1
        # Find the matching closing fence: same character, at least as long,
        # with no info string.
        j = i + 1
        body: list[str] = []
        closed = False
        while j < len(lines):
            cm = FENCE_RE.match(lines[j])
            if (
                cm
                and cm.group("ticks")[0] == ticks[0]
                and len(cm.group("ticks")) >= len(ticks)
                and not cm.group("info").strip()
            ):
                closed = True
                break
            body.append(lines[j])
            j += 1

        tag = info.strip().split(",")[0].split()[0] if info.strip() else ""
        if tag == "ritz":
            if not closed:
                raise FenceError(f"{doc}:{open_line}: unterminated ```ritz fence")
            code = "\n".join(_dedent(body, indent))
            blocks.append(block_from_fence(doc, open_line, info, code))

        i = (j + 1) if closed else (i + 1)
    return blocks


def _dedent(body: list[str], indent: str) -> list[str]:
    """Remove the fence's own indentation from each body line."""
    if not indent:
        return body
    out = []
    for line in body:
        out.append(line[len(indent):] if line.startswith(indent) else line.lstrip())
    return out


# ---------------------------------------------------------------------------
# Compiling
# ---------------------------------------------------------------------------

BODY_PREAMBLE = "fn __doc_example() -> i32\n"
BODY_EPILOGUE = "    return 0\n"


def render(block: Block) -> str:
    """Turn a block into a compilable translation unit."""
    if block.mode == "items":
        return block.code.rstrip() + "\n"
    # `body`: statements, indented one level into a wrapper function. The
    # trailing `return 0` makes the wrapper well-formed regardless of
    # whether the snippet ends in a return of its own.
    indented = "\n".join(
        ("    " + line) if line.strip() else line for line in block.code.rstrip().splitlines()
    )
    return BODY_PREAMBLE + indented + "\n" + BODY_EPILOGUE


def compile_cmd(compiler: str, src: Path, out: Path) -> list[str]:
    """The command that compiles one doc example to LLVM IR."""
    binary, _ = COMPILERS[compiler]
    if binary is None:
        return [sys.executable, str(RITZ0), str(src), "-o", str(out)]
    # ritz1's CLI: <input> -o <output> [-I <ritz root>].  -I is how it finds
    # `ritzlib.*`, the same root RITZ_PATH names for ritz0.
    return [str(binary), str(src), "-o", str(out), "-I", str(RITZ_ROOT)]


def missing_compiler(compiler: str) -> str | None:
    """Why `compiler` cannot run, or None.  A missing binary is an error,
    never a skip: a gate that passes because it had nothing to run is the
    defect this script exists to prevent."""
    binary, hint = COMPILERS[compiler]
    if binary is not None and not binary.is_file():
        return f"{compiler} is not built ({binary}); run `{hint}` first."
    return None


def compiler_identity(compiler: str = "ritz0") -> str:
    """A human-readable record of *which* compiler validated the docs.

    The value goes in the report so a green run names its reference, rather
    than leaving "it compiled" to mean "on somebody's machine, once".
    """
    rev = "unknown"
    try:
        rev = subprocess.run(
            ["git", "-C", str(RITZ_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        pass
    path = COMPILERS[compiler][0] or RITZ0
    top = RITZ_ROOT.parent.parent
    rel = path.relative_to(top) if path.is_relative_to(top) else path
    if compiler == "ritz0":
        return f"ritz0 ({rel}) at {rev}, {sys.executable.rsplit('/', 1)[-1]}"
    return f"{compiler} ({rel}) at {rev}"


def compile_block(block: Block, workdir: Path, compiler: str = "ritz0") -> Result:
    if block.no_compile_reason:
        return Result(block, ok=True, skipped=True, detail=block.no_compile_reason)

    stem = f"{block.doc.stem}_{block.line}"
    src = workdir / f"{stem}.ritz"
    src.write_text(render(block), encoding="utf-8")

    # RITZ_PATH is how the import resolver finds `ritzlib.*`. Without it a
    # documented `import ritzlib.io` fails for a reason that has nothing to
    # do with the documentation, so we set it rather than requiring every
    # caller to remember (the Makefile exports it; a bare `python3
    # tools/check_doc_examples.py` does not).
    env = dict(os.environ)
    env.setdefault("RITZ_PATH", str(RITZ_ROOT))

    proc = subprocess.run(
        compile_cmd(compiler, src, workdir / f"{stem}.ll"),
        capture_output=True,
        text=True,
        cwd=str(RITZ_ROOT),
        env=env,
        timeout=120,
    )
    output = (proc.stdout + proc.stderr).strip()

    if block.expect_error:
        if proc.returncode == 0:
            return Result(
                block,
                ok=False,
                detail=(
                    f"block is marked expect-error={block.expect_error!r} but it "
                    f"COMPILED. Either the compiler gained this feature and the "
                    f"prose is now wrong, or the fence is."
                ),
            )
        if compiler != "ritz0":
            return ritz1_refusal(block, proc.returncode, output, compiler)
        if block.expect_error not in output:
            return Result(
                block,
                ok=False,
                detail=(
                    f"block failed, but not with the declared diagnostic.\n"
                    f"    expected substring: {block.expect_error}\n"
                    f"    actual: {_indent_output(output)}"
                ),
            )
        return Result(block, ok=True, detail=f"failed as declared: {block.expect_error}")

    if block.expect_runtime_error:
        if proc.returncode != 0:
            return Result(block, ok=False, detail=(
                "block is marked expect-runtime-error but did not compile:"
                + _indent_output(output)))
        if problem := verify_ir(workdir / f"{stem}.ll"):
            return Result(block, ok=False, detail=_invalid_ir_detail(problem, compiler))
        return run_block(block, workdir, stem, compiler)

    if proc.returncode != 0:
        return Result(block, ok=False, detail=_indent_output(output))
    if problem := verify_ir(workdir / f"{stem}.ll"):
        return Result(block, ok=False, detail=_invalid_ir_detail(problem, compiler))
    return Result(block, ok=True)


# `.ritz:4:13:` in an expect-error value pins where the diagnostic points.
POSITION_RE = re.compile(r"\.ritz:(\d+):(\d+):")


def ritz1_refusal(block: Block, returncode: int, output: str, compiler: str) -> Result:
    """Judge an expect-error block that a ritz1-family compiler refused.

    The fence's text is ritz0's diagnostic, and ritz1's wording differs by
    design (its parser has no `Expected IDENT, got MUT`), so ritz1 is held
    to what the example *means*: it must refuse the block with a diagnostic,
    not crash on it, and where the fence pins a `.ritz:L:C` position ritz1's
    diagnostic must point at the same place.  (AGAST #3928.)
    """
    if returncode < 0 or not output:
        return Result(block, ok=False, detail=(
            f"block is marked expect-error, and {compiler} refused it without a "
            f"diagnostic (exit {returncode}): a crash, not a refusal."
            + _indent_output(output)))
    if pos := POSITION_RE.search(block.expect_error or ""):
        want = f".ritz:{pos.group(1)}:{pos.group(2)}:"
        if want not in output:
            return Result(block, ok=False, detail=(
                f"block failed, but {compiler}'s diagnostic does not point at the "
                f"declared position.\n"
                f"    expected position: {want}\n"
                f"    actual: {_indent_output(output)}"))
    return Result(block, ok=True, detail=f"refused by {compiler} as declared")


# LLVM's global context is not thread-safe and `run` compiles blocks on a
# thread pool, so every parse goes through this lock.  A parse costs
# milliseconds; the ritz0 subprocess it follows costs far more.
_LLVM_LOCK = threading.Lock()


def verify_ir(ll: Path) -> str | None:
    """Parse and verify the IR ritz0 wrote; return the problem, or None.

    AGAST #1358: ritz0 exiting 0 does not mean its output is IR.  For seven
    months the documented `token.kind == TokenKind.Ident` idiom compiled to
    a .ll holding `icmp eq` on a struct, which only clang's parser rejects,
    and this gate reported it "compiled as declared" because it stopped at
    the exit code.  Parsing is the minimum that makes "compiled" true.
    """
    import llvmlite.binding as llvm

    text = ll.read_text(encoding="utf-8")
    with _LLVM_LOCK:
        try:
            module = llvm.parse_assembly(text)
            module.verify()
        except RuntimeError as exc:
            return str(exc).strip() or type(exc).__name__
        module.close()
    return None


def _invalid_ir_detail(problem: str, compiler: str = "ritz0") -> str:
    return (
        f"{compiler} exited 0 but emitted invalid IR (a compiler bug, not a doc "
        "bug; clang would reject this at build time):" + _indent_output(problem)
    )


def run_block(block: Block, workdir: Path, stem: str, compiler: str = "ritz0") -> Result:
    """Link an expect-runtime-error block freestanding, run it, check stderr.

    ritz0 emits its own `_start` for a file with a `main`, so the link needs
    no runtime object and no ritzlib: the same `-nostdlib` link
    ritz0/test_attr_validation.py uses.  ritz1 emits no `_start`, so its
    output is linked with RITZ1_START.
    """
    exe = workdir / f"{stem}.exe"
    start = [] if compiler == "ritz0" else [str(RITZ1_START)]
    link = subprocess.run(
        ["clang", "-Wno-override-module", "-O0", str(workdir / f"{stem}.ll"), *start,
         "-o", str(exe), "-nostdlib", "-no-pie"],
        capture_output=True, text=True, timeout=120,
    )
    if link.returncode != 0:
        return Result(block, ok=False, detail=(
            "block compiled but did not link:" + _indent_output(link.stderr.strip())))
    proc = subprocess.run([str(exe)], capture_output=True, timeout=30)
    stderr = proc.stderr.decode("utf-8", errors="replace")
    if proc.returncode == 0:
        return Result(block, ok=False, detail=(
            "block is marked expect-runtime-error but the program exited 0. "
            "Either the behaviour changed and the prose is now wrong, or the "
            "fence is."))
    if block.expect_runtime_error not in stderr:
        return Result(block, ok=False, detail=(
            f"program failed (exit {proc.returncode}), but not with the declared stderr.\n"
            f"    expected substring: {block.expect_runtime_error!r}\n"
            f"    actual: {_indent_output(stderr.strip())}"))
    return Result(block, ok=True, detail=f"failed at run time as declared (exit {proc.returncode})")


def _indent_output(output: str) -> str:
    lines = output.splitlines() or ["(no output)"]
    if len(lines) > 12:
        lines = lines[:6] + [f"    ... {len(lines) - 12} lines elided ..."] + lines[-6:]
    return ("\n" + "\n".join("      " + ln for ln in lines)).rstrip()


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run(docs: list[Path], jobs: int, verbose: bool, compiler: str = "ritz0",
        known: dict[tuple[str, str, str], str] | None = None) -> Report:
    known = KNOWN_FAILURES if known is None else known
    blocks: list[Block] = []
    for doc in docs:
        blocks.extend(extract_blocks(doc))

    report = Report()
    with tempfile.TemporaryDirectory(prefix="ritz-doc-examples-") as tmp:
        workdir = Path(tmp)
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            for result in pool.map(lambda b: compile_block(b, workdir, compiler), blocks):
                result = apply_known_failure(result, compiler, known)
                report.results.append(result)
                if verbose:
                    mark = ("SKIP" if result.skipped else "KNOWN" if result.known
                            else "ok" if result.ok else "FAIL")
                    print(f"  {mark:5} {result.block.where}")
    report.results.extend(stale_known_failures(blocks, docs, compiler, known))
    report.results.sort(key=lambda r: (str(r.block.doc), r.block.line))
    return report


def apply_known_failure(result: Result, compiler: str,
                        known: dict[tuple[str, str, str], str]) -> Result:
    """Hold a KNOWN_FAILURES entry to its claim (AGAST #3928).

    A listed block that fails is reported as known, citing its ticket; a
    listed block that now passes fails the run, so the entry is deleted when
    the ritz1 bug is fixed rather than outliving it.
    """
    b = result.block
    reason = known.get((compiler, b.doc.name, b.digest))
    if reason is None or result.skipped:
        return result
    if result.ok:
        return Result(b, ok=False, detail=(
            f"listed in KNOWN_FAILURES ({reason}) but it now passes under "
            f"{compiler}. Delete the entry ({compiler!r}, {b.doc.name!r}, "
            f"{b.digest!r}) from tools/check_doc_examples.py."))
    return Result(b, ok=True, known=reason, detail=result.detail)


def stale_known_failures(blocks: list[Block], docs: list[Path], compiler: str,
                         known: dict[tuple[str, str, str], str]) -> list[Result]:
    """A failure Result per entry naming a checked doc but no block in it."""
    present = {(b.doc.name, b.digest) for b in blocks}
    by_name = {d.name: d for d in docs}
    stale = []
    for (comp, doc_name, digest), reason in sorted(known.items()):
        if comp != compiler or doc_name not in by_name or (doc_name, digest) in present:
            continue
        ghost = Block(doc=by_name[doc_name], line=0, code="")
        stale.append(Result(ghost, ok=False, detail=(
            f"KNOWN_FAILURES entry ({comp!r}, {doc_name!r}, {digest!r}) -- {reason} -- "
            f"matches no block in {doc_name}: the block was edited or removed. "
            f"Re-check it under {compiler} and re-key or delete the entry.")))
    return stale


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Compile every fenced ```ritz example in the given documents.",
        epilog=(
            "Fence attributes: body, expect-error=\"...\", "
            "expect-runtime-error=\"...\", no-compile=\"reason\". "
            "See the module docstring for what each one promises."
        ),
    )
    ap.add_argument("docs", nargs="+", type=Path, help="markdown documents to check")
    ap.add_argument("--list", action="store_true", help="list blocks; do not compile")
    ap.add_argument("-j", "--jobs", type=int, default=8, help="parallel compiles (default 8)")
    ap.add_argument("-v", "--verbose", action="store_true", help="one line per block")
    ap.add_argument("--compiler", choices=sorted(COMPILERS), default="ritz0",
                    help="compiler to check the examples with (default ritz0)")
    args = ap.parse_args(argv)

    missing = [d for d in args.docs if not d.is_file()]
    if missing:
        for d in missing:
            print(f"error: no such document: {d}", file=sys.stderr)
        return 1

    try:
        if args.list:
            for doc in args.docs:
                for b in extract_blocks(doc):
                    kind = (
                        "no-compile"
                        if b.no_compile_reason
                        else ("expect-error" if b.expect_error
                              else ("expect-runtime-error" if b.expect_runtime_error
                                    else b.mode))
                    )
                    print(f"{b.where}\t{kind}")
            return 0

        if why := missing_compiler(args.compiler):
            print(f"error: {why}", file=sys.stderr)
            return 1
        print(f"=== Checking doc examples with {compiler_identity(args.compiler)} ===")
        started = time.monotonic()
        report = run(args.docs, jobs=args.jobs, verbose=args.verbose, compiler=args.compiler)
        elapsed = time.monotonic() - started
    except FenceError as exc:
        print(f"\nFENCE ERROR: {exc}", file=sys.stderr)
        return 1

    if report.skips:
        print(f"\n{len(report.skips)} block(s) opted out of compilation:")
        for r in report.skips:
            print(f"  {r.block.where}: {r.detail}")

    if report.known:
        print(f"\n{len(report.known)} block(s) are known {args.compiler} failures:")
        for r in report.known:
            print(f"  {r.block.where} [{r.block.digest}]: {r.known}")

    for r in report.failures:
        print(f"\nFAIL {r.block.where} [{args.compiler}, digest {r.block.digest}]")
        print("  " + shlex.quote(str(r.block.doc)) + f" line {r.block.line}")
        print(f"  {r.detail}")
        first = r.block.code.strip().splitlines()[:6]
        print("  block:")
        for ln in first:
            print(f"      {ln}")

    total = len(report.results)
    print(
        f"\n{args.compiler}: {len(report.compiled)}/{total} blocks compiled as declared, "
        f"{len(report.skips)} opted out, {len(report.known)} known failures, "
        f"{len(report.failures)} failed, in {elapsed:.1f}s."
    )
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
