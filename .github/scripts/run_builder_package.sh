#!/usr/bin/env bash
# Run one package through a builder image and fail on a build or test
# failure, or a run that reports zero tests (AGAST #4825, #4826, #4847).
# main.yml's builder-matrix job calls this once per matrix entry, from the
# root of the checkout under test.
#
#   run_builder_package.sh [--build-only] <image> <package-rel-path> <out-dir>
#
#   --build-only         build, don't test: the package has no tests
#                        (tools/builder_matrix.py's `build_only`)
#   <image>              the builder image ref to run, e.g. rz-builder:ci,
#                        main.yml's builder-image job's build of this commit
#   <package-rel-path>   workspace-relative package path, e.g.
#                        projects/buddhafinger; normalized, so
#                        projects/../bench/x is bench/x, and refused if it
#                        leaves the workspace
#   <out-dir>            host directory for the container's /out; created
#                        if missing
#
# Mounts the whole checkout read-only as the entrypoint's workspace
# (RZ_ROOT=/ws, AGAST #4847) and runs the image's entrypoint (AGAST #4823)
# on the package's in-tree path. The sources are this commit's, all of them:
# a package's tests read other packages' files (prism reads angelo's font
# fixture, buddhafinger ritz1's keyword table), and the image's /rz ships
# only what a build imports. The compiler is still the image's own
# ritz1_selfhosted, which the entrypoint links into its private workspace;
# the checkout has none. --network=none: the run needs none.
# --security-opt seccomp=unconfined: Docker's default profile returns EPERM
# for io_uring_setup / io_uring_enter / io_uring_register, and ritzlib's
# tests call them.
#
# The container's own exit status is already 0 only when the build
# succeeded and every test passed (projects/builder/README.md); this script
# adds, through check_builder_summary.py (shared with Woodpecker's
# woodpecker_builder_step.sh, AGAST #4846), one more check the image can't make for itself: a package whose
# summary reports zero tests passed is a silently-empty run, not a green
# one, so it fails here even though the container exited 0 (projects/
# builder/summary.py's "No tests found, skipping" parses to passed=0,
# ok=true -- correct for a library with none, but a result this script
# cannot tell apart from the suite not running at all without the count).
# A passing test.sh is a suite that ran, counted or not (rllvm's is pytest).
# A package with no tests at all is run --build-only instead, which the
# matrix decides from the package's files, not from the run.
#
# Exit: 0 built (and, unless --build-only, tested, at least one test
# passed); 1 the container's own failure, a missing summary.json, or zero
# tests passed; 2 bad arguments.
set -euo pipefail

usage() {
    echo "usage: run_builder_package.sh [--build-only] <image> <package-rel-path> <out-dir>" >&2
    exit 2
}
build_only=0
if [[ ${1:-} == --build-only ]]; then
    build_only=1
    shift
fi
[[ $# -eq 3 ]] || usage
image=$1 pkg=$2 out=$3

# -s: lexical, no symlink is followed out of the workspace.
pkg=$(realpath -ms --relative-to="$PWD" "$PWD/$pkg")
if [[ $pkg == .. || $pkg == ../* || $pkg == . ]]; then
    echo "run_builder_package: '$2' is outside the workspace" >&2
    exit 2
fi
[[ -f "$pkg/ritz.toml" ]] || {
    echo "run_builder_package: no ritz.toml in '$pkg'" >&2
    exit 2
}

mode=()
[[ $build_only -eq 1 ]] && mode=(--build-only)
mkdir -p "$out"
docker run --rm --network=none --security-opt seccomp=unconfined \
    -e RZ_ROOT=/ws \
    -v "$PWD:/ws:ro" \
    -v "$out:/out" \
    "$image" "${mode[@]}" "$pkg"

summary="$out/summary.json"
[[ -f "$summary" ]] || {
    echo "run_builder_package: $pkg: $summary is missing after the run" >&2
    exit 1
}
python3 "$(dirname "$0")/check_builder_summary.py" "$summary" "$pkg" "$build_only"
