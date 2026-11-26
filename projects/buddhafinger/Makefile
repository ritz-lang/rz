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

.PHONY: all build test
all: build

# ritz1-bootstrap builds ritz1 + ritz1_selfhosted; a no-op when both are current.
build:
	$(MAKE) -C ../ritz ritz1-bootstrap
	$(RZ) build buddhafinger --compiler $(COMPILER)

test: build
	$(RZ) test buddhafinger --compiler $(COMPILER)
