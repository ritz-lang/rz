# Goliath Makefile — delegates to the workspace `rz` tool.
#
# Goliath is described by ritz.toml. `rz` reads that and drives the compiler,
# dependency resolution and RITZ_PATH. This file exists so `make` still does
# the right thing in this directory — it is not a second build definition.
#
# Why this file was rewritten:
#
#   * `make test` shelled out to ./build_tests.sh, deleted in db2402e
#     ("Remove 40 legacy build scripts") when every project moved to
#     `rz build` / `rz test`. The Makefile kept calling it, so the target had
#     been failing with "No such file or directory" ever since.
#
#   * `make build` was broken in a quieter way: the .PHONY `build` target and
#     the `build/` output directory are the same name, so make merged them,
#     warned "overriding recipe for target 'build'", dropped the compile rule
#     as circular, and left a target whose entire effect was `mkdir -p build`.
#     It exited 0 while compiling nothing.

RZ := $(CURDIR)/../../rz
PROJECT := goliath

.PHONY: all build test clean check-env help

all: build

build:
	@$(RZ) build $(PROJECT)

test:
	@$(RZ) test $(PROJECT)

clean:
	@$(RZ) clean $(PROJECT)

check-env:
	@test -x "$(RZ)" || (echo "ERROR: rz not found at $(RZ)" && exit 1)
	@echo "rz: $(RZ)"

help:
	@echo "Goliath — content-addressable filesystem for Harland"
	@echo ""
	@echo "This Makefile delegates to the workspace 'rz' tool."
	@echo ""
	@echo "Targets:"
	@echo "  build      - rz build $(PROJECT)"
	@echo "  test       - rz test $(PROJECT)"
	@echo "  clean      - rz clean $(PROJECT)"
	@echo "  check-env  - verify rz is reachable"
	@echo ""
	@echo "The old test flag variants (-v / -f / -l) are not exposed by"
	@echo "'rz test' yet; run the built test binary directly if you need them."
