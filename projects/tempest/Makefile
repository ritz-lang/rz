# Tempest Browser — delegates to the workspace `rz` tool.
#
# Tempest is described by ritz.toml ([[bin]] tempest, [[bin]] tempest-tab).
# `rz` reads that and drives the compiler, dependency resolution and
# RITZ_PATH. This file exists so `make` still does the right thing in this
# directory — it is not a second build definition.
#
# Why this file was rewritten:
#
#   * `make test` shelled out to ./scripts/build_tests.sh, deleted in db2402e
#     ("Remove 40 legacy build scripts") when every project moved to
#     `rz build` / `rz test`. The target had been failing ever since.
#
#   * `make build` did not build. It ran the `check` target instead, with the
#     comment "full build requires Prism, Iris, etc." — dependencies that
#     ritz.toml now resolves, so `rz build tempest` does the real thing.
#
#   * The compiler paths were rooted at $(HOME)/dev/ritz-lang/ritz, which is
#     not where ritz lives in this monorepo (projects/ritz). Worse, the file
#     *assigned* RITZ_PATH, clobbering the value CI exports. Paths are now
#     derived from $(CURDIR) so they follow the checkout.

WORKSPACE := $(CURDIR)/../..
RZ := $(WORKSPACE)/rz
PROJECT := tempest

# Used only by the `check` target below.
RITZ0 := python3 $(WORKSPACE)/projects/ritz/ritz0/ritz0.py
LIB_SOURCES = $(wildcard lib/*.ritz)

# Tempest sources use RERITZ syntax ([[test]] rather than @test).
export RITZ_SYNTAX=reritz

.PHONY: all build test clean check help

all: build

build:
	@$(RZ) build $(PROJECT)

test:
	@$(RZ) test $(PROJECT)

clean:
	@$(RZ) clean $(PROJECT)

# Type check the library without producing binaries. Kept because rz has no
# check-only mode and this is a fast inner-loop for library work.
check:
	@echo "Type checking..."
	@for f in $(LIB_SOURCES); do \
		echo "  Checking $$f"; \
		RITZ_PATH=$(WORKSPACE)/projects $(RITZ0) "$$f" -o /dev/null --no-runtime 2>&1 || exit 1; \
	done
	@echo "Type check complete."

help:
	@echo "Tempest Browser"
	@echo ""
	@echo "This Makefile delegates to the workspace 'rz' tool."
	@echo ""
	@echo "Targets:"
	@echo "  build  - rz build $(PROJECT)"
	@echo "  test   - rz test $(PROJECT)"
	@echo "  clean  - rz clean $(PROJECT)"
	@echo "  check  - type check lib/ without building"
	@echo ""
	@echo "The old test flag variants (-v / -l) are not exposed by 'rz test'"
	@echo "yet; run the built test binary directly if you need them."
