# Buddhafinger's dedicated build and test entry point (AGAST #4813, epic
# #4782; docs/BUDDHAFINGER_PROPOSAL.md "Tests and build isolation").
#
# The editor builds and tests with ritz1_selfhosted only, so every rz call
# here passes the compiler explicitly: rz's default is ritz0. rz.toml's
# [workspace.exclude] keeps the package out of `rz build --all` / `rz test
# --all`. This target is for local dev, where ritz1_selfhosted comes from a
# host build (ritz1-bootstrap, below); CI's gate is main.yml's
# builder-matrix job (AGAST #4825, #4826), which runs the published builder
# image's own ritz1_selfhosted in a container instead of calling this
# Makefile. projects/ritz/tools/test_buddhafinger_isolation.py and
# tools/test_builder_matrix.py pin all of that.

COMPILER := ritz1_selfhosted
RZ := ../../rz

.PHONY: all build test bench-build bench bench-check
all: build

# ritz1-bootstrap builds ritz1 + ritz1_selfhosted; a no-op when both are
# current. ritz-lsp is built for test_lsp_editor.ritz's real-server smoke.
build:
	$(MAKE) -C ../ritz ritz1-bootstrap
	$(RZ) build ritz-lsp --compiler $(COMPILER)
	$(RZ) build buddhafinger --compiler $(COMPILER)

test: build
	$(RZ) test buddhafinger --compiler $(COMPILER)

# The benchmark workloads (AGAST #4821; bench/README.md): a release build of
# buddhafinger-bench, then each workload in its own process, so each peak
# memory is its own. bench-check also holds every result to its limit in
# bench/limits.txt and fails on any over. Kept out of `test`: timings are
# not functional results.
BENCH := build/release/buddhafinger-bench
BENCH_DIR ?= /tmp/buddhafinger-bench
BENCH_WORKLOADS := lines lines-hl long long-hl
BENCH_SOURCES := src/core/editor.ritz ../ritz/ritz1/src/parser_gen.ritz

bench-build:
	$(MAKE) -C ../ritz ritz1-bootstrap
	$(RZ) build buddhafinger --release --compiler $(COMPILER)

bench: bench-build
	mkdir -p $(BENCH_DIR)
	set -e; for w in $(BENCH_WORKLOADS); do $(BENCH) $$w $(BENCH_DIR); done; \
	for f in $(BENCH_SOURCES); do $(BENCH) src $(BENCH_DIR) $$f; done

bench-check: bench-build
	mkdir -p $(BENCH_DIR)
	set -e; for w in $(BENCH_WORKLOADS); do $(BENCH) $$w $(BENCH_DIR) --check bench/limits.txt; done; \
	for f in $(BENCH_SOURCES); do $(BENCH) src $(BENCH_DIR) $$f --check bench/limits.txt; done
