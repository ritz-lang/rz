#!/bin/bash
# rllvm: the CLI and parser tests, then the clang-oracle corpus. An entry
# rllvm does not lower yet is an expected failure naming what it waits on
# (-rx prints each); it never passes or skips silently.
set -u
cd "$(dirname "$0")"
# The bin links build_package makes here, or in test_run_dir's shadow.
[ -x rllvm ] && export RLLVM="$PWD/rllvm"
[ -x rllvm-ir ] && export RLLVM_IR="$PWD/rllvm-ir"
exec python3 -m pytest -q -rxX -p no:cacheprovider tests
