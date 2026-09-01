# Spire Makefile — delegates to the workspace `rz` tool.
#
# Spire is described by ritz.toml (a test_only package with a [[lib]] and a
# [[test]] binary). `rz` reads that and drives the compiler, dependency
# resolution and RITZ_PATH. This file exists so `make` still does the right
# thing in this directory — it is not a second build definition.
#
# Why this file was rewritten:
#
#   * `make test` shelled out to ./scripts/build_tests.sh, deleted in db2402e
#     ("Remove 40 legacy build scripts") when every project moved to
#     `rz build` / `rz test`. The target had been failing ever since.
#
#   * `make build` looped over lib/*.ritz invoking ritz0 with
#     `2>/dev/null || true`, so every compile error was discarded and the
#     target always exited 0. CI reported Spire green while it was not being
#     compiled in any meaningful sense.

RZ := $(CURDIR)/../../rz
PROJECT := spire

.PHONY: all build test clean submodules dev loc help

all: build

# Initialise/update git submodules. Kept: this is Spire-specific and has no
# equivalent in rz.
submodules:
	git submodule update --init --recursive

build:
	@$(RZ) build $(PROJECT)

test:
	@$(RZ) test $(PROJECT)

clean:
	@$(RZ) clean $(PROJECT)

# Quick dev cycle
dev: clean build test

# Count lines of code
loc:
	@echo "Lines of code in Spire:"
	@find lib -name "*.ritz" -exec wc -l {} + | tail -1
	@echo ""
	@echo "Lines of test code:"
	@find test -name "*.ritz" -exec wc -l {} + 2>/dev/null | tail -1 || echo "  0 total"

help:
	@echo "Spire — MVRSPT web framework for Ritz"
	@echo ""
	@echo "This Makefile delegates to the workspace 'rz' tool."
	@echo ""
	@echo "Targets:"
	@echo "  build       - rz build $(PROJECT)"
	@echo "  test        - rz test $(PROJECT)"
	@echo "  clean       - rz clean $(PROJECT)"
	@echo "  submodules  - git submodule update --init --recursive"
	@echo "  dev         - clean + build + test"
	@echo "  loc         - count lines of code"
	@echo ""
	@echo "The old test flag variants (-v / -q / -f / -l) are not exposed by"
	@echo "'rz test' yet; run the built test binary directly if you need them."
