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
does not do what its fence says it does.

Usage:
    python3 tools/check_doc_examples.py DOC.md [DOC.md ...]
    python3 tools/check_doc_examples.py --list DOC.md      # no compiling
    python3 tools/check_doc_examples.py -v DOC.md          # per-block lines

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

``body`` exists because much of the prose illustrates a statement or two
rather than a whole program.  Those blocks are wrapped in a ``fn`` and a
trailing ``return 0`` before compiling, so they are still *compiled* --
the fragment-ness is handled by a preamble, not by an exemption.

``expect-error`` is how a document demonstrates a mistake.  Such blocks
are not skipped: they must fail, and they must fail with the diagnostic
the prose claims they produce.  A block that starts compiling because the
compiler grew a feature is a documentation bug, and this reports it.

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
import os
import re
import shlex
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path


# projects/ritz/tools/check_doc_examples.py -> projects/ritz
RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"

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
    no_compile_reason: str | None = None

    @property
    def where(self) -> str:
        return f"{self.doc}:{self.line}"


@dataclass
class Result:
    block: Block
    ok: bool
    detail: str = ""
    skipped: bool = False


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
        return [r for r in self.results if r.ok and not r.skipped]


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
    block = Block(doc=doc, line=line, code=code)

    known = {"body", "items", "expect-error", "no-compile"}
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


def compiler_identity() -> str:
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
    rel = RITZ0.relative_to(RITZ_ROOT.parent.parent) if RITZ0.is_relative_to(
        RITZ_ROOT.parent.parent
    ) else RITZ0
    return f"ritz0 ({rel}) at {rev}, {sys.executable.rsplit('/', 1)[-1]}"


def compile_block(block: Block, workdir: Path) -> Result:
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
        [sys.executable, str(RITZ0), str(src), "-o", str(workdir / f"{stem}.ll")],
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

    if proc.returncode != 0:
        return Result(block, ok=False, detail=_indent_output(output))
    return Result(block, ok=True)


def _indent_output(output: str) -> str:
    lines = output.splitlines() or ["(no output)"]
    if len(lines) > 12:
        lines = lines[:6] + [f"    ... {len(lines) - 12} lines elided ..."] + lines[-6:]
    return ("\n" + "\n".join("      " + ln for ln in lines)).rstrip()


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run(docs: list[Path], jobs: int, verbose: bool) -> Report:
    blocks: list[Block] = []
    for doc in docs:
        blocks.extend(extract_blocks(doc))

    report = Report()
    with tempfile.TemporaryDirectory(prefix="ritz-doc-examples-") as tmp:
        workdir = Path(tmp)
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            for result in pool.map(lambda b: compile_block(b, workdir), blocks):
                report.results.append(result)
                if verbose:
                    mark = "SKIP" if result.skipped else ("ok" if result.ok else "FAIL")
                    print(f"  {mark:4} {result.block.where}")
    report.results.sort(key=lambda r: (str(r.block.doc), r.block.line))
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Compile every fenced ```ritz example in the given documents.",
        epilog=(
            "Fence attributes: body, expect-error=\"...\", no-compile=\"reason\". "
            "See the module docstring for what each one promises."
        ),
    )
    ap.add_argument("docs", nargs="+", type=Path, help="markdown documents to check")
    ap.add_argument("--list", action="store_true", help="list blocks; do not compile")
    ap.add_argument("-j", "--jobs", type=int, default=8, help="parallel compiles (default 8)")
    ap.add_argument("-v", "--verbose", action="store_true", help="one line per block")
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
                        else ("expect-error" if b.expect_error else b.mode)
                    )
                    print(f"{b.where}\t{kind}")
            return 0

        print(f"=== Checking doc examples with {compiler_identity()} ===")
        report = run(args.docs, jobs=args.jobs, verbose=args.verbose)
    except FenceError as exc:
        print(f"\nFENCE ERROR: {exc}", file=sys.stderr)
        return 1

    if report.skips:
        print(f"\n{len(report.skips)} block(s) opted out of compilation:")
        for r in report.skips:
            print(f"  {r.block.where}: {r.detail}")

    for r in report.failures:
        print(f"\nFAIL {r.block.where}")
        print("  " + shlex.quote(str(r.block.doc)) + f" line {r.block.line}")
        print(f"  {r.detail}")
        first = r.block.code.strip().splitlines()[:6]
        print("  block:")
        for ln in first:
            print(f"      {ln}")

    total = len(report.results)
    print(
        f"\n{len(report.compiled)}/{total} blocks compiled as declared, "
        f"{len(report.skips)} opted out, {len(report.failures)} failed."
    )
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
