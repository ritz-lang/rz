#!/bin/bash
# rld against its oracles (`ld.lld`, and `clang -nostdlib` for --hosted): each
# corpus program linked both ways, both run, and their output and exit status
# compared; the freestanding PIEs compared on their dynamic tags and
# relocations (DESIGN.md "rld tests").
set -u
cd "$(dirname "$0")"
# The bin link build_package makes here, or in test_run_dir's shadow.
[ -x rld ] && export RLD="$PWD/rld"
exec python3 -m pytest -q -rxX -p no:cacheprovider tests
