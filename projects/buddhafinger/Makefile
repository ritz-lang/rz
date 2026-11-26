# Buddhafinger's dedicated build and test entry point (AGAST #4813, epic
# #4782; docs/BUDDHAFINGER_PROPOSAL.md "Tests and build isolation").
#
# The editor builds and tests with ritz1_selfhosted only, so every rz call
# here passes the compiler explicitly: rz's default is ritz0. rz.toml's
# [workspace.exclude] keeps the package out of `rz build --all` / `rz test
# --all`, and main.yml runs `make -C projects/buddhafinger test` instead.
# projects/ritz/tools/test_buddhafinger_isolation.py pins both.

COMPILER := ritz1_selfhosted
RZ := ../../rz

.PHONY: all build test
all: build

# ritz1-bootstrap builds ritz1 + ritz1_selfhosted; a no-op when both are current.
build:
	$(MAKE) -C ../ritz ritz1-bootstrap
	$(RZ) build buddhafinger --compiler $(COMPILER)

test: build
	$(RZ) test buddhafinger --compiler $(COMPILER)
