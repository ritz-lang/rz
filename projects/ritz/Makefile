# 🎭 Ritz Language Build System
#
# Usage:
#   make            - Run all tests
#   make test       - Build and test all examples
#   make unit       - Run Python unit tests only
#   make ritz       - Run .ritz language tests
#   make build      - Build all examples (no tests)
#   make clean      - Remove build artifacts
#   make list       - List all packages
#
# Individual packages:
#   make build-<name>  - Build a specific package
#   make test-<name>   - Build and test a specific package

.PHONY: all test unit ritz ritz1 ritz1-bootstrap build clean list help valgrind regression regression-quick check-no-s-strings matrix matrix-full matrix-quick regen-check smoke

PYTHON ?= python3
VALGRIND ?= valgrind --error-exitcode=1 --leak-check=full -q

# Set RITZ_PATH for standard library lookup
# This allows 'import ritzlib.sys' to resolve to $(ROOT)/ritzlib/sys.ritz
ROOT := $(shell pwd)
export RITZ_PATH := $(ROOT)

# -j level for every ritz1 build (AGAST #1802): RITZ1_JOBS, else min(nproc, 8).
# The #1659 .d files make -j safe; a cold bootstrap goes 278 s -> 101 s with
# byte-identical binaries.  See scripts/ritz1-jobs.sh for why it is a cap.
RITZ1_J := $(shell RITZ1_JOBS='$(RITZ1_JOBS)' sh scripts/ritz1-jobs.sh)

all: test

# Run everything
# AGAST #98: check-no-s-strings runs first so any resurrected s"..." literal
# fails CI before we burn compile cycles on it.
test: check-no-s-strings check-doc-examples check-manifest-spec unit tools-unit harness-selftest ritz ritz1 examples
	@echo "✓ All tests passed!"

# AGAST #98 guard: ensure no s"..." span-string literals leak back in.
# The prefix was removed after bare "..." was flipped to StrView (same
# { ptr, len } shape), so any new s"..." is either dead syntax or a
# regression. docs/archive/ is excluded (frozen snapshots).
check-no-s-strings:
	@echo "=== Checking no s\"...\" literals remain ==="
	@$(PYTHON) tools/check_no_s_strings.py .

# AGAST #1311 guard: every fenced ```ritz block in the language documentation
# is compiled by ritz0. The docs linked from the top-level README spent seven
# months teaching `let mut`, `&T` and `String::from` — syntax the compiler
# rejects, in one case with a bespoke migration diagnostic we wrote and then
# never applied to the document that taught it. Prose with no mechanism that
# can fail will rot; this is the mechanism.
#
# DOC_EXAMPLE_DOCS is the checked set. Adding a document here is how a doc
# becomes load-bearing; there is deliberately no way to exempt one silently.
DOC_EXAMPLE_DOCS := \
	docs/LANGUAGE_SPEC.md \
	docs/STDLIB_REFERENCE.md \
	docs/STANDARD.md \
	docs/ECOSYSTEM.md

.PHONY: check-doc-examples
check-doc-examples:
	@echo "=== Compiling documentation examples ==="
	@$(PYTHON) tools/check_doc_examples.py $(DOC_EXAMPLE_DOCS)

# AGAST #3928. The same documents under ritz1 and ritz1_selfhosted: a doc
# example ritz0 accepts and ritz1 refuses (or miscompiles) used to pass the
# gate. Known ritz1 failures are gate = "doc" entries in the workspace's
# known-failures/<ticket>.toml (#3963, #1834). ~1 s per compiler once built.
.PHONY: check-doc-examples-ritz1
check-doc-examples-ritz1: ritz1-bootstrap
	@$(PYTHON) tools/check_doc_examples.py --compiler ritz1 $(DOC_EXAMPLE_DOCS)
	@$(PYTHON) tools/check_doc_examples.py --compiler ritz1_selfhosted $(DOC_EXAMPLE_DOCS)

# docs/RITZ_TOML_SPEC.md is generated from manifest.py's schema, the one rz
# and build.py validate every ritz.toml / rz.toml against (AGAST #1837).
# `manifest-spec` regenerates it; `check-manifest-spec` (CI) fails on drift
# and prints the diff.
.PHONY: manifest-spec check-manifest-spec
manifest-spec:
	@$(PYTHON) manifest.py --spec > docs/RITZ_TOML_SPEC.md
	@echo "✓ wrote docs/RITZ_TOML_SPEC.md"

check-manifest-spec:
	@$(PYTHON) manifest.py --check-spec docs/RITZ_TOML_SPEC.md

# Python unit tests for the tools/ scripts themselves. These existed but were
# wired into nothing — tools/test_check_no_s_strings.py had never been run by
# make or by CI. A guard whose own tests do not run is a guard on the honour
# system.
#
# Parallel like `unit` below, with the same PYTEST_J knob (AGAST #2792: 312 s
# serial in the gate).  A test that writes a fixed path another test uses must
# make that write safe (atomic rename, private tmp dir) or, failing that, take
# an xdist_group mark, which --dist loadgroup honours.
.PHONY: tools-unit
tools-unit:
	@echo "=== Running tools/ unit tests (-n $(PYTEST_J)) ==="
	@$(PYTHON) -m pytest -q -n $(PYTEST_J) --dist loadgroup tools/

# The tools/ tests that read compiler SOURCES (ritz0/, ritz1/, grammars/,
# runtime/): the ritz1 ratchets, arch/metrics/emitter-import checks, the
# kind-ladder ratchet, the ritz0/ritzgen/grammar source checks and the
# down-only pins (test_standard_callers.py).  A subset of tools-unit (~15 s
# vs ~4-6 min), run by every room's pre-REAP smoke
# (.claude/skills/rz-iterate/smoke-plan.sh; AGAST #4587: train 814a64f4 went
# red on test_ritz1_kind_match.py, which it never ran) and on each train tip
# before it gates (`train.sh precheck`, AGAST #4672).  A new source-reading
# test or pin belongs under one of these names.
#
# Not test_ritz1_incremental_deps.py (AGAST #4672): it builds ritz1 four
# times, ~50 s, and is a build test, not a source ratchet.  tools-unit runs it.
TOOLS_RATCHETS = tools/test_ritz1_*.py tools/test_ritz0_*.py tools/test_ritzgen_*.py \
	tools/test_grammar_*.py tools/test_enum_ast_nodes.py tools/test_corpus_parses.py \
	tools/test_known_failures.py tools/test_ci_local.py tools/test_standard_callers.py
TOOLS_RATCHETS_OUT = tools/test_ritz1_incremental_deps.py

#
# The ratchets under ritz0/tests run too (AGAST #4622: train 2026-11-24 went
# red on test_ritz1_sema_walk_layout.py, which this target never collected).
# They are picked by rule, not by list, so a new one cannot drift out:
# `-m inproc` (ritz0/conftest.py item 13) is every ritz0 test that is not
# `integration` and asks for no ritz1-building fixture, so it compiles
# nothing (spawn_guard, item 9).  ~2400 tests: ~60 s serial, so they run
# under xdist with --no-ritz1-build (item 14), which keeps the controller
# from building ritz1 first (item 4).  A separate pytest from tools/ (the
# read guard, #4032, fails tools tests in a ritz0 session), and run alongside
# it, so the target takes about as long as the slower half; each half gets
# half the cores (RATCHETS_J; not PYTEST_J, which sizes ONE suite).  ~15 s on
# omegalisk idle (AGAST #4672; ~65 s before).
# tools/test_ritz0_source_ratchets.py holds the target to this.
RATCHETS_J ?= $(shell j=$$(( $$(nproc) / 2 )); [ $$j -ge 2 ] && echo $$j || echo 2)
.PHONY: tools-ratchets tools-ratchets-tools tools-ratchets-ritz0
tools-ratchets:
	@$(MAKE) --no-print-directory -j2 --output-sync=target tools-ratchets-tools tools-ratchets-ritz0

tools-ratchets-tools:
	@echo "=== Running tools/ source-reading ratchets (-n $(RATCHETS_J)) ==="
	@$(PYTHON) -m pytest -q -n $(RATCHETS_J) --dist loadgroup $(filter-out $(TOOLS_RATCHETS_OUT),$(wildcard $(TOOLS_RATCHETS)))

tools-ratchets-ritz0:
	@echo "=== Running ritz0 in-process tests: source ratchets (-m inproc, -n $(RATCHETS_J)) ==="
	@cd ritz0 && $(PYTHON) -m pytest -q --disable-plugin-autoload -p xdist -n $(RATCHETS_J) --dist loadgroup --no-ritz1-build -m inproc

# ritz1's measurements: modules, sizes, import graph and cycles, where each
# check runs, long functions.  Printed, never committed (AGAST #3896: a block
# of them in ritz1/ARCHITECTURE.md made every ritz1 commit conflict); the
# doc's invariants are checked by tools/test_ritz1_arch.py in tools-unit.
.PHONY: arch-report
arch-report:
	@$(PYTHON) tools/ritz1_arch.py

# M1.3's thresholds as a one-way ratchet over the numbers arch-report prints
# (tools/ritz1_metrics_baseline.json, plus one acceptance file per ticket in
# tools/ratchet_accept/): a metric may improve, not worsen.  Runs in
# tools-unit (tools/test_ritz1_ratchet.py); this target is for humans.
# Accept a deliberate feature cost with `--update`, which writes only this
# ticket's raised metrics so two rooms never share a hunk (AGAST #4447).
.PHONY: arch-ratchet
arch-ratchet:
	@$(PYTHON) tools/ritz1_ratchet.py

# Every examples/**/test/*.ritz [[test]] suite, with ritz0 (AGAST #3729).
# rz.toml keeps examples out of `rz test --all`, and regression.sh runs each
# example's test.sh but never its test/*.ritz, so until this target nothing
# ran them. Fails on an unlisted failure, on a stale known-failures entry
# (gate = "examples"), and if fewer files ran than exist on disk. See tools/example_tests.py.
.PHONY: example-tests
example-tests:
	@echo "=== Running example [[test]] suites ==="
	@$(PYTHON) tools/example_tests.py

# Self-tests for scripts/regression.sh's own logic. Same problem as tools-unit
# above, one layer down: scripts/test-regression-stage5.sh existed since the
# Stage 5 work and was wired into NOTHING — not make, not CI. A test that never
# runs is documentation with a shebang.
#
# Globbed, not listed, so a new self-test is picked up by existing. The suite
# these protect is the one that gates every merge, and both of the holes they
# cover (Stage 5's allowlist escape hatch, #1359's rotted example allowlist)
# were things the end-to-end run reported green.
.PHONY: harness-selftest
harness-selftest:
	@echo "=== Running regression harness self-tests ==="
	@found=0; rc=0; \
	for t in scripts/test-regression-*.sh; do \
	    [ -e "$$t" ] || continue; \
	    found=$$((found + 1)); \
	    echo "--- $$t"; \
	    bash "$$t" || rc=1; \
	done; \
	if [ $$found -eq 0 ]; then \
	    echo "no scripts/test-regression-*.sh found — the glob has rotted"; exit 1; \
	fi; \
	echo "$$found harness self-test(s) run."; \
	exit $$rc

# Smoke tier — AGAST #1803, design projects/larb/review/4/fast-iteration.md §4.
# "Fully broken" in <= 2 min cold, <= 60 s warm, stopping at the first failure:
# s-strings + regen-check, `pytest -m smoke` (ritz0/conftest.py SMOKE_FILES),
# incremental ritz1, a ritz0+ritz1 canary matrix (tools/smoke_canaries.txt),
# and ritz1 compiling tokens_gen.ritz to IR clang accepts.  Runs first in
# run-gate.sh and in main.yml's bootstrap job; rooms run it before a gate.
smoke:
	@$(PYTHON) tools/smoke.py

# AGAST #2456: start every server/CLI and make real requests, against the
# debug binaries `./rz build --all` leaves behind. CI runs it in build-all;
# strict xfails cite the tickets that own today's failures. ~30s.
.PHONY: smoke-stack
smoke-stack:
	@$(PYTHON) tools/smoke_stack $(ARGS)

# Run exactly what .github/workflows/main.yml runs, by PARSING it — AGAST #1363.
#
# Not a restatement of the gate commands. A remembered list drifts from CI, and
# every drift is a green tick asserting less than you think:
#   `./regression.sh` instead of `scripts/regression.sh`      -> exit 127
#   `make -C projects/ritz ...` from inside projects/ritz/ritz0 -> exit 2
# Both look like a suite complaining rather than a command that never ran.
#
# Defaults to the `bootstrap` job (the compiler gate). `--jobs` runs everything.
# The room gate runs build-all, test-all and bootstrap (run-gate.sh).
#   make ci-local                       bootstrap
#   make ci-local ARGS="--list"         what CI declares
#   make ci-local ARGS="--jobs"         everything
#
# One deliberate reordering (AGAST #3456): before the first step, ci-local runs
# the ritz0 test files the last commits changed (tools/likely_tests.py), so a
# likely failure shows minutes into a gate, not ten; the pytest step then
# --ignore's them.  ARGS="--no-likely-first" runs the steps exactly as declared.
.PHONY: ci-local
ci-local:
	@$(PYTHON) tools/ci_local.py $(ARGS)

# Python unit tests for ritz0 compiler, in parallel under pytest-xdist (AGAST
# #1804).  PYTEST_J workers, default 8: with -n auto a 12-core host would run
# 12 on a VM shared with the gate and the task rooms.  `--dist loadgroup` keeps
# xdist_group("tree") tests on one worker; see ritz0/conftest.py.  PYTEST_J=0
# runs serially.  --disable-plugin-autoload -p xdist: the suite needs no
# other installed plugin, and a venv's (django, anyio, ...) cost every one of
# ~31k tests (AGAST #2793, as in main.yml).
PYTEST_J ?= 8
unit:
	@echo "=== Running ritz0 unit tests (-n $(PYTEST_J)) ==="
	@cd ritz0 && $(PYTHON) -m pytest -q --disable-plugin-autoload -p xdist -n $(PYTEST_J) --dist loadgroup

# Run .ritz language tests (test levels)
ritz:
	@echo "=== Running .ritz language tests ==="
	@$(PYTHON) build.py ritz-tests

# Build the ritz1 compiler with ritz0 (incremental; fails if ritz1 fails to compile).
# This target used to run `build.py ritz1-tests`, a hardcoded list of 15 lexer
# tests that had all moved to docs/archive/ritz1_old/ -- it skipped every file and
# exited 0, so `make test` carried a gate that could not fail (AGAST #1485).
# Those tests described a ritz1 that no longer exists and were deleted, not
# repointed.  Keep this target defined and .PHONY: without it, the ritz1/
# directory would satisfy `make ritz1` and it would report "Nothing to be done".
ritz1:
	@echo "=== Building ritz1 ==="
	@$(MAKE) -j$(RITZ1_J) -C ritz1 ritz1

# Build ritz1 AND ritz1_selfhosted once, in parallel (AGAST #1802).  main.yml
# runs this before pytest, so the ~80 module fixtures that `make -C ritz1 ritz1`
# find it current instead of racing a cold serial build, and matrix-full and
# regression.sh Stage 4 reuse both binaries.
ritz1-bootstrap:
	@echo "=== Building ritz1 + ritz1_selfhosted (-j$(RITZ1_J)) ==="
	@$(MAKE) -j$(RITZ1_J) -C ritz1 bootstrap

# ritz1's unit suites: every ritz1/test/*.ritz is a [[test]] file importing
# ritz1/src modules (AGAST #1556).  Fails on a file with no tests and on no
# files at all.  CI's bootstrap job runs it; ~5 s.
.PHONY: ritz1-unit
ritz1-unit:
	@$(PYTHON) tools/ritz1_unit.py

# ritzlib's [[test]] suites under ritz1 AND ritz1_selfhosted (AGAST #3805).
# The regression matrix was the only ritz1 run, so whole ritzlib test files
# could rot under ritz1 unseen (#3766).  ritz0's run is the train's package
# step (#3909).  CI's bootstrap job runs this after ritz1-bootstrap, which
# makes the prerequisite a no-op; ~20 s per compiler.
.PHONY: ritzlib-tests-ritz1
ritzlib-tests-ritz1: ritz1-bootstrap
	cd ../.. && ./rz test ritz/ritzlib/tests --compiler ritz1
	cd ../.. && ./rz test ritz/ritzlib/tests --compiler ritz1_selfhosted

# Every workspace package built by ritz1 (AGAST #4272) and ritz1_selfhosted
# (#4317): goal 2 of the self-hosting loop, "ritz1 builds every package ritz0
# builds".  --all, not a list, so a new package is covered the day it lands;
# one a compiler cannot build is a known-failures/ `build` entry naming that
# compiler and its ticket, and strict xpass deletes it once it builds.  All 28
# built under each on 0a839f97: ~56 s / ~58 s cold, ~9 s warm, on 8 workers.
.PHONY: build-all-ritz1
build-all-ritz1: ritz1-bootstrap
	cd ../.. && ./rz build --all --compiler ritz1
	cd ../.. && ./rz build --all --compiler ritz1_selfhosted

# Build and test all examples (always runs)
.PHONY: examples
examples:
	@$(PYTHON) build.py test --all

# Build all examples (no tests)
build:
	@$(PYTHON) build.py build --all

# List all packages
list:
	@$(PYTHON) build.py list

# Clean build artifacts
clean:
	@$(PYTHON) build.py clean
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.ritz.sig" -delete 2>/dev/null || true  # pre-#1807 in-tree sigs
# No `rm -f /tmp/*.ll /tmp/*.o` here (AGAST #3178): /tmp is shared with every
# other room and gate on the host, and that glob deleted their files.

# Pattern rules for individual packages
build-%:
	@$(PYTHON) build.py build $*

test-%:
	@$(PYTHON) build.py test $*

# Run Tier 1 examples through valgrind for memory checking
valgrind: build
	@echo "=== Running valgrind memory checks ==="
	@$(VALGRIND) examples/01_hello/hello
	@$(VALGRIND) examples/03_echo/echo hello world >/dev/null
	@$(VALGRIND) examples/04_true_false/true
	@echo "test" | $(VALGRIND) examples/05_cat/cat >/dev/null
	@printf "line1\nline2\n" | $(VALGRIND) examples/06_head/head -n 1 >/dev/null
	@printf "a b c\n" | $(VALGRIND) examples/07_wc/wc >/dev/null
	@$(VALGRIND) examples/08_seq/seq 5 >/dev/null
	@$(VALGRIND) examples/10_sleep/sleep 0.001
	@echo "✓ All valgrind checks passed!"

# Validation matrix: every [[test]] fn in ritz0/test/*.ritz × {ritz0, ritz1,
# ritz1_selfhosted}. Files are discovered, not listed, and a floor fails the
# run if fewer fns executed than are on disk (AGAST #1371).
# See docs/VALIDATION.md for the full validation workflow.
#
# Three escalating thoroughness levels:
#   matrix-quick — incremental ritz1 build + ritz1-only matrix       (~30-60s)
#   matrix       — alias for matrix-quick (the common pre-commit gate)
#   matrix-full  — incremental ritz1 + selfhost build + full matrix  (~4-5min)
#
# DO NOT add a `clean` step here. Make's dep tracking is correct; if it
# isn't, that's a Makefile bug. See docs/VALIDATION.md "Hard rules".
matrix-quick: regen-check | _matrix_ritz1_built
	@$(PYTHON) tools/run_regression_matrix.py --compiler ritz1

matrix: matrix-quick

matrix-full: regen-check | _matrix_ritz1_built
	@echo "=== Full matrix (ritz0 + ritz1 + ritz1_selfhosted) ==="
	@echo "    This will incrementally rebuild ritz1_selfhosted (~3 min if ritz1 source changed)."
	@$(PYTHON) tools/run_regression_matrix.py --rebuild

# Guard against the cardinal sin: hand-editing a generated file instead of
# regenerating from grammars/ritz1.grammar.  Runs the generator into a tmp
# dir and diffs each generated file against its committed copy.  If they
# differ, the committed file has drifted from the grammar or the generator —
# fix the source, regen, or both.
#
# Covers every generated file that is committed verbatim: parser_gen,
# tokens_gen and lexer_scan_gen (lexer_setup_gen until #1821; it was unchecked until #1436, which had
# to change the generator and the generated file in step). ast_helpers.ritz is
# NOT checked: it is hand-written.  The generator emits only a stub listing the
# constructor names the grammar actions call, so there is no generated copy.
#
# A generator crash fails the check. It used to pass: the diff ran behind `&&`,
# so a failed generator skipped it and the trailing `rm` returned 0.
#
# See docs/VALIDATION.md "Hard rules" — the grammar is the source of truth.
REGEN_PAIRS := parser.ritz:parser_gen.ritz tokens.ritz:tokens_gen.ritz lexer_scan_gen.ritz:lexer_scan_gen.ritz
regen-check:
	@TMPDIR=$$(mktemp -d) ; \
	  if ! $(PYTHON) tools/ritzgen_py/ritz_generator.py grammars/ritz1.grammar \
	    --monolithic --output-dir $$TMPDIR >$$TMPDIR/.gen.log 2>&1; then \
	    echo "❌ regen-check FAILED — the generator itself failed:" ; \
	    tail -10 $$TMPDIR/.gen.log ; \
	    rm -rf $$TMPDIR ; \
	    exit 1 ; \
	  fi ; \
	  status=0 ; \
	  for pair in $(REGEN_PAIRS); do \
	    gen=$${pair%%:*} ; committed=ritz1/src/$${pair##*:} ; \
	    if ! diff -q $$TMPDIR/$$gen $$committed >/dev/null 2>&1; then \
	      echo "❌ regen-check FAILED — $$committed has drifted from grammars/ritz1.grammar + the generator." ; \
	      echo "   Either:" ; \
	      echo "     (a) edit the grammar or tools/ritzgen_py and regenerate," ; \
	      echo "     (b) revert hand-edits to $$committed." ; \
	      echo "   First few diff lines:" ; \
	      diff $$TMPDIR/$$gen $$committed | head -10 ; \
	      status=1 ; \
	    fi ; \
	  done ; \
	  rm -rf $$TMPDIR ; \
	  exit $$status

# Internal: ensure ritz1 binary is up-to-date before running the matrix.
.PHONY: _matrix_ritz1_built
_matrix_ritz1_built:
	@$(MAKE) -j$(RITZ1_J) -C ritz1 ritz1 >/dev/null 2>&1 || $(MAKE) -j$(RITZ1_J) -C ritz1 ritz1

# Regression test suite (all tiers)
regression:
	@./scripts/regression.sh

# Quick regression (skip self-hosted bootstrap)
regression-quick:
	@./scripts/regression.sh --quick

help:
	@echo "🎭 Ritz Language Build System"
	@echo ""
	@echo "Targets:"
	@echo "  make          - Run all tests (unit + ritz + ritz1 + examples)"
	@echo "  make test     - Same as above"
	@echo "  make smoke    - Smoke tier: is anything fully broken? (<= 2 min, stops at first failure)"
	@echo "  make unit     - Run Python unit tests (ritz0)"
	@echo "  make ritz     - Run .ritz language tests (test levels)"
	@echo "  make ritz1    - Build the ritz1 compiler (make -j -C ritz1 ritz1)"
	@echo "  make ritz1-bootstrap - Build ritz1 + ritz1_selfhosted in parallel (RITZ1_JOBS caps -j)"
	@echo "  make examples - Build and test example packages"
	@echo "  make build    - Build all examples (no tests)"
	@echo "  make list     - List all packages"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make valgrind - Run valgrind memory checks on Tier 1 examples"
	@echo "  make matrix       - Pre-commit gate: incremental ritz1 + ritz1-only matrix (~30-60s)"
	@echo "  make matrix-full  - Pre-push gate: incremental ritz1 + selfhost + full matrix (~4-5min)"
	@echo "  make regen-check  - Verify the generated ritz1 sources match a fresh regen from the grammar"
	@echo "  make regression       - Full regression suite (all 4 tiers)"
	@echo "  make regression-quick - Quick regression (skip bootstrap)"
	@echo "  make check-no-s-strings - Guard that no s\"...\" literals leak back in"
	@echo ""
	@echo "  See docs/VALIDATION.md for the full validation workflow."
	@echo ""
	@echo "Individual packages:"
	@echo "  make build-<name>  - Build a specific package"
	@echo "  make test-<name>   - Test a specific package"
	@echo ""
	@echo "Examples:"
	@echo "  make test-hello"
	@echo "  make build-05_cat"
