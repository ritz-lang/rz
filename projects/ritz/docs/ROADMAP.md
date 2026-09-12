# Ritz Roadmap

Ritz is a systems programming language that compiles to LLVM IR and targets Linux
syscalls directly, with no libc. It is bootstrapped: `ritz0` is a Python reference
compiler, `ritz1` is written in Ritz and compiles itself.

## This document holds structure, not status

There are no test counts, example counts, milestone checkboxes, percentages,
phase tables or dates below this line. That is deliberate.

The previous version of this file was written once and never updated. By the time
it was deleted it described ritz1 as reaching "Milestone 1: `fn main() -> i32 {
return 42 }` compiles" and estimated "~1 week to self-hosting" — while ritz1 had
long since compiled itself, and while that example program could not compile at
all, because Ritz is indentation-based and has no brace blocks. It also carried a
hand-written date a year in the past.

Every one of those errors was a *duplicated fact*: something true elsewhere,
copied here, and then left behind when the original moved. So this file no longer
duplicates facts. It records the things that do not change month to month, and
points at the commands and the tracker that hold everything that does.

**If you want to know the current state of the project, run something.** The
commands are in the next section and they are the same ones CI runs.

## Where the authoritative answers live

| Question | Authority |
|---|---|
| What is being worked on, what is blocked, why | **AGAST** — the task tracker. Not any file in this repo. |
| Does the compiler work, right now | `make -C projects/ritz ci-local` — runs CI's job list, in CI's order |
| Which examples does each compiler accept | `projects/ritz/scripts/regression.sh` — the 5-stage differential suite |
| Which failures are known and excused | `scripts/regression-known-failures.txt` (ritz0) and `scripts/regression-known-failures-ritz1.txt` (ritz1 / ritz1_selfhosted) |
| What the language *is* | `docs/LANGUAGE_SPEC.md` — the normative standard, and its examples are compiled by CI |
| How to build and test a package | the workspace-root `./rz` CLI, and `projects/ritz/build.py` |

Two notes that save time:

- `make ci-local` must be run with `-C projects/ritz`. There is no root `Makefile`;
  a bare `make ci-local` fails with `No rule to make target`, which exits 2 and
  reads like a test failure.
- `build.py` takes a **path** to a package, not a bare name, and needs
  `RITZ_PATH` set for anything that imports `ritzlib`.

### The allowlists are the real roadmap

`regression-known-failures*.txt` is the most honest statement of remaining work in
the repo: an entry is a claim that the *compiler* cannot yet handle an example.
Both files are strict in both directions — an allowlisted example that starts
compiling fails the suite, so the lists cannot quietly rot green.

Read their header comments before trusting an entry. Several entries have been
delisted after turning out to be bugs in the *example*, not the compiler, and the
headers record each case. The standing rule is written there: **an anonymous
compiler error is not evidence about whose bug it is.**

The gap between the two files is the most useful number nobody needs to maintain:
ritz0 accepts nearly the whole corpus, and ritz1 parity is the larger remaining
effort. Run the suite to see the current split.

## The plan: build in layers, from the bottom

The organising decision for this project is to stop working breadth-first across
the whole ecosystem and instead establish a trustworthy base and climb. Each layer
is only started when the one below it is *gated* — not merely working.

**Layer 0 — a trustworthy standard library.** `ritzlib` compiles, has a real CI
gate, and conforms to a written standard. This is tracked as an AGAST epic with
subtasks for: writing the normative standard and retiring competing style docs;
giving ritzlib a CI gate of its own; making its test suite green; and converting
it to the standard's idioms.

**Layer 1 onwards — climb the tier ladder one rung at a time.** The example corpus
is already organised into tiers that form the ladder: basics, stdlib, coreutils,
applications, async. A rung is done when both compilers accept it and it is gated.

Layers above 0 are deliberately not decomposed here. Decomposing work that is not
about to start is how the previous roadmap filled up with phases that were
obsolete before anyone read them.

### What "done" means for a layer

A layer is complete when all four hold:

1. It compiles under `ritz0` **and** under `ritz1`, with no new allowlist entries.
2. Its tests run in a gate that can **fail the build**. A suite nothing runs is
   not a suite; a gate that cannot go red is not a gate.
3. Its documentation is compiled by `make check-doc-examples`, so its examples
   cannot drift from the compiler.
4. Nothing below it regressed — which the differential suite checks by comparing
   compilers against each other, not against a recorded number.

Criterion 2 carries the most weight and is the easiest to fake. The repo's history
is full of suites that reported success while running a fraction of what they
claimed, or nothing at all. When in doubt, break something on purpose and confirm
the gate goes red.

## Durable invariants

These are properties of the project rather than items of work, and they are not
expected to change:

- **No libc.** Direct syscalls. A missing capability gets implemented in the
  language, not worked around by linking something else.
- **The bootstrap must close.** `ritz1` compiles itself, and `ritz1` and
  `ritz1_selfhosted` must accept an *identical set* of programs. The fixed-point
  check is the last stage of the regression suite.
- **Equivalence is behavioural, not textual.** The suite compares program output
  and exit codes across compilers. It does not require byte-identical IR, and
  nothing in the repo has ever checked for that — earlier docs claiming a
  bit-for-bit IR gate were describing an aspiration.
- **Tests are written before implementations**, and a new gate is proven by
  watching it fail first.
- **A documented command must work.** A command in a doc that silently does
  nothing is worse than no documentation, because it reports success. Several have
  been found and fixed; the habit that catches them is running what you write.

## Keeping this file honest

If you are about to add a status figure, a count, a date or a checkbox to this
document: don't. Put it in AGAST, or make it the output of a command and cite the
command instead. That single rule is the entire difference between this file and
the one it replaced.
