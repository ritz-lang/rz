#!/usr/bin/env bash
# One package of the builder matrix on huburght's Woodpecker (AGAST #4846).
# .woodpecker/builder.yml runs it once per package, from the root of the
# checkout Woodpecker cloned:
#
#   woodpecker_builder_step.sh [--build-only] <package-rel-path>
#
# Woodpecker's kubernetes backend runs the step as a pod whose image IS the
# builder image of the commit (ghcr.io/ritz-lang/rz-builder:<commit>), so
# there is no `docker run` here: this is run_builder_package.sh's container
# half. The image's entrypoint (`rz-builder`, AGAST #4823) builds and tests
# the package with the image's ritz1_selfhosted, the checkout standing in
# for the image's sources (RZ_ROOT, AGAST #4847), and writes its logs and
# summary.json to a directory outside the checkout. check_builder_summary.py
# then fails a run that reported zero tests, as on GitHub.
#
# The entrypoint refuses a path that leaves the workspace or has no
# ritz.toml (exit 2) and echoes its build and test logs as it runs.
#
# Exit: 0 built (and, unless --build-only, at least one test passed);
# 1 the entrypoint's own failure, a missing summary.json, or zero tests
# passed; 2 bad arguments.
set -euo pipefail

usage() {
    echo "usage: woodpecker_builder_step.sh [--build-only] <package-rel-path>" >&2
    exit 2
}
build_only=0
mode=()
if [[ ${1:-} == --build-only ]]; then
    build_only=1
    mode=(--build-only)
    shift
fi
[[ $# -eq 1 ]] || usage
pkg=$1

out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT
rc=0
RZ_ROOT=$PWD RZ_OUT=$out/out rz-builder "${mode[@]}" "$pkg" || rc=$?

summary=$out/out/summary.json
if [[ ! -f $summary ]]; then
    echo "run_builder_package: $pkg: summary.json is missing after the run (exit $rc)" >&2
    exit 1
fi
check=0
python3 "$(dirname "$0")/check_builder_summary.py" "$summary" "$pkg" "$build_only" || check=$?
if [[ $rc -ne 0 ]]; then
    echo "run_builder_package: $pkg: rz-builder exited $rc" >&2
    exit 1
fi
exit "$check"
