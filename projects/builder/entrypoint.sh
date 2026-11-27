#!/bin/bash
# Build and test one package with the image's ritz1_selfhosted (AGAST #4823).
#
#   docker run --rm --network=none --security-opt seccomp=unconfined \
#     -v "$PWD/projects/sage:/src/projects/sage:ro" \
#     -v "$PWD/out:/out" \
#     rz-builder:<tag> /src/projects/sage
#
#   docker run --rm --network=none --security-opt seccomp=unconfined \
#     -v "$PWD/out:/out" \
#     rz-builder:<tag> --build-only projects/harland
#
# The package is an in-tree path under the workspace (projects/sage,
# bench/regressions/...), or an absolute path of a mounted directory. A mounted package is copied into
# a private workspace; its path dependencies and ritzlib resolve against the
# image's sources. The mount is only read. Binaries, object files, the two
# logs and summary.json go to /out (or $RZ_OUT). Exit 0 only when the build
# succeeded and every test passed. --build-only skips tests (harland's
# kernel: the image has no QEMU).
#
# The compiler is the image's ritz1_selfhosted, named by $RITZ1 and by
# `./rz build|test --compiler ritz1_selfhosted`. The default compiler is
# never used. The two must be the same file.
#
# The workspace is the image's /rz, or $RZ_ROOT: a whole checkout mounted
# read-only (main.yml's builder-matrix, AGAST #4847), whose sources then
# replace the image's. The compiler stays the image's: a checkout's own
# ritz1/build is never used, and the image's ritz1_selfhosted is linked where
# the pipeline looks for it.
#
# The CAS (compiled modules: the package's, ritzlib's, ritzunit's) is private
# to the run unless $RZ_BUILDER_CACHE names a writable directory, mounted
# for the purpose (AGAST #4857). The store is then
# $RZ_BUILDER_CACHE/<cache key>, so a run on the same compiler reuses the
# objects of the last; any other `ritz1-*` store there (an older compiler)
# is deleted, and after the run the store is trimmed to
# $RZ_BUILDER_CACHE_MAX_BYTES (default 1536MiB). A CAS key already covers
# the compiler, clang, the flags and every source in a module's import
# closure, so a stale object is never reused. Concurrent runs on one store
# are safe (cas.py: atomic renames, a per-key lock). A $RZ_BUILDER_CACHE the
# run can't write warns and runs uncached: a missing cache never fails a
# package.
#
#   rz-builder --cache-key
#
# prints the key and exits: ritz1-<first 16 of ritz1_selfhosted's sha256,
# the image's dev.ritz.ritz1-selfhosted.sha256 label>-clang-<version>.
set -euo pipefail

RZ_ROOT=${RZ_ROOT:-/rz}
OUT=${RZ_OUT:-/out}
BUILD_ONLY=0
CACHE_KEY_ONLY=0

usage() {
    sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; $d'
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build-only) BUILD_ONLY=1; shift ;;
        --cache-key) CACHE_KEY_ONLY=1; shift ;;
        -h|--help) usage ;;
        --) shift; break ;;
        -*) echo "rz-builder: unknown option $1" >&2; usage ;;
        *) break ;;
    esac
done
[[ $# -eq $((1 - CACHE_KEY_ONLY)) ]] || usage
PKG_ARG=${1:-}

# summary.py sits beside this script in the repo and under /usr/local/lib
# in the image.
SCRIPT=$(readlink -f "$0")
if [[ -f $(dirname "$SCRIPT")/summary.py ]]; then
    SUMMARY=$(dirname "$SCRIPT")/summary.py
elif [[ -f /usr/local/lib/rz-builder/summary.py ]]; then
    SUMMARY=/usr/local/lib/rz-builder/summary.py
else
    echo "rz-builder: summary.py not found next to $SCRIPT" >&2
    exit 2
fi

SELFHOSTED=projects/ritz/ritz1/build/ritz1_selfhosted
IMAGE_RITZ1=/rz/$SELFHOSTED
if [[ -z ${RITZ1:-} ]]; then
    if [[ $RZ_ROOT != /rz && -x $IMAGE_RITZ1 ]]; then
        RITZ1=$IMAGE_RITZ1
    else
        RITZ1=$RZ_ROOT/$SELFHOSTED
    fi
fi
[[ -x $RITZ1 ]] || { echo "rz-builder: ritz1_selfhosted is not executable at $RITZ1" >&2; exit 2; }

cache_key() {
    local sha clang_version
    sha=$(sha256sum "$RITZ1" | cut -c1-16)
    clang_version=$(clang --version 2>/dev/null \
        | sed -n '1s/.*clang version \([0-9][0-9.]*\).*/\1/p')
    if [[ -z $clang_version ]]; then
        echo "rz-builder: no clang version from \`clang --version\`" >&2
        return 2
    fi
    printf 'ritz1-%s-clang-%s\n' "$sha" "$clang_version"
}
if [[ $CACHE_KEY_ONLY -eq 1 ]]; then
    cache_key
    exit
fi
[[ -d $RZ_ROOT/projects/ritz ]] || { echo "rz-builder: $RZ_ROOT is not a builder workspace" >&2; exit 2; }

if [[ $PKG_ARG == /* ]]; then
    SRC=$PKG_ARG
else
    # An in-tree path names its own place in the workspace, under projects/
    # or not (bench/regressions/...). -s: lexical; refuse one that leaves.
    IN_TREE=$(realpath -ms --relative-to=/ "/$PKG_ARG")
    if [[ $IN_TREE == .. || $IN_TREE == ../* || $IN_TREE == . ]]; then
        echo "rz-builder: $PKG_ARG is outside the workspace" >&2
        exit 2
    fi
    SRC=$RZ_ROOT/$IN_TREE
fi
[[ -f $SRC/ritz.toml ]] || { echo "rz-builder: no ritz.toml in $SRC" >&2; exit 2; }

# Where the package sits in the workspace. A path that contains a projects/
# component keeps it (projects/sage, projects/ritz/ritzlib/tests), so path
# dependencies land on the image's copies. Anything else is projects/<name>.
rel_of() {
    local src=$1
    local -a parts=()
    local IFS=/
    read -ra parts <<< "${src#/}"
    local i j rel
    for ((i = 0; i < ${#parts[@]}; i++)); do
        if [[ ${parts[i]} == projects ]]; then
            rel=projects
            for ((j = i + 1; j < ${#parts[@]}; j++)); do
                rel=$rel/${parts[j]}
            done
            printf '%s\n' "$rel"
            return 0
        fi
    done
    printf 'projects/%s\n' "$(basename "$src")"
}
if [[ -n ${IN_TREE:-} ]]; then
    REL=$IN_TREE
else
    REL=$(rel_of "$SRC")
fi

if ! mkdir -p "$OUT" || ! touch "$OUT/.write-test"; then
    echo "rz-builder: $OUT is not writable" >&2
    exit 2
fi
rm -f "$OUT/.write-test"
rm -rf "$OUT/bin" "$OUT/obj" "$OUT/build" "$OUT/summary.json" \
    "$OUT/build.log" "$OUT/test.log" "$OUT/cas-stats.jsonl"

# One fixed path, not mktemp's (AGAST #4857): the workspace has no checkout
# or package marker, so a CAS key names the package's own modules by their
# absolute path, and a random one missed them on every run of a persistent
# store. A container has /tmp to itself; a path already taken (two runs on
# one host) falls back to a private one, which is only uncached.
WS=${TMPDIR:-/tmp}/rz-builder-ws
mkdir "$WS" 2>/dev/null || WS=$(mktemp -d)
cleanup() {
    if [[ -n ${WS:-} && -d $WS ]]; then
        rm -rf "$WS"
    fi
}
trap cleanup EXIT

# rz's WORKSPACE_ROOT is the script's own directory after symlinks, so the
# script is a real file in the workspace, not a link back to the image.
cp -aL "$RZ_ROOT/rz" "$WS/rz"
chmod +x "$WS/rz"
ln -s "$RZ_ROOT/rz.toml" "$WS/rz.toml"
if [[ -d $RZ_ROOT/known-failures ]]; then
    ln -s "$RZ_ROOT/known-failures" "$WS/known-failures"
fi

# One entry of a source directory, placed in the workspace: a Python file is
# copied, anything else linked. Python resolves a script's symlink, so a
# linked build.py would import build_pipeline from the source tree, look for
# ritz1_selfhosted there and put the runtime objects next to it, in a
# read-only mount (AGAST #4847). Ritz sources stay links: the import
# resolver names a module by its real path, and a copy beside a link would
# be two definitions of one module.
place() {
    local child=$1 dest=$2
    if [[ $child == *.py && -f $child && ! -L $child ]]; then
        cp -p "$child" "$dest"
    else
        ln -s "$child" "$dest"
    fi
}

# A symlink to a directory, replaced by a real directory of its entries
# (place), so a new file created inside it (a build/, a runtime .o) stays in
# the workspace.
explode() {
    local link=$1 target child
    [[ -L $link ]] || return 0
    target=$(readlink -f "$link")
    [[ -d $target ]] || return 0
    rm "$link"
    mkdir "$link"
    for child in "$target"/*; do
        [[ -e $child ]] || continue
        case $(basename "$child") in
            build|.ritz-cache*) continue ;;
        esac
        place "$child" "$link/$(basename "$child")"
    done
}

# Parents of the package are real directories. Siblings come from the image,
# so a mounted sage still imports the image's ritzlib and path dependencies.
# `build` is never linked: the build creates its own, in the workspace.
materialize() {
    local rel=$1 src=$2
    local -a parts=()
    local IFS=/
    read -ra parts <<< "$rel"
    local dest_parent=$WS image_parent=$RZ_ROOT
    local i part next image_here child name
    for ((i = 0; i < ${#parts[@]} - 1; i++)); do
        part=${parts[i]}
        next=${parts[i + 1]}
        mkdir -p "$dest_parent/$part"
        image_here=$image_parent/$part
        if [[ -d $image_here && ! -L $dest_parent/$part ]]; then
            for child in "$image_here"/*; do
                [[ -e $child ]] || continue
                name=$(basename "$child")
                [[ $name == "$next" ]] && continue
                case $name in
                    build|.ritz-cache*) continue ;;
                esac
                if [[ ! -e $dest_parent/$part/$name ]]; then
                    place "$child" "$dest_parent/$part/$name"
                fi
            done
        fi
        dest_parent=$dest_parent/$part
        image_parent=$image_here
    done
    local dest=$WS/$rel
    rm -rf "$dest"
    mkdir -p "$dest"
    # Top-level build/ and .git stay behind. The source is only read.
    tar -C "$src" --exclude=./build --exclude=./.git --exclude=./.ritz-cache \
        -cf - . | tar -C "$dest" -xf -
}

materialize "$REL" "$SRC"
# A package outside projects/ (bench/...) has no projects/ of its own:
# materialize only fills its own parents. Link the workspace's, then make it
# a real directory like the rest.
if [[ ! -e $WS/projects ]]; then
    ln -s "$RZ_ROOT/projects" "$WS/projects"
fi
explode "$WS/projects"
explode "$WS/projects/ritz"
explode "$WS/projects/ritz/runtime"

# A mounted workspace's compiler is the image's (header): link it where the
# pipeline looks, unless the workspace's own path already is $RITZ1.
if [[ $(readlink -f "$WS/$SELFHOSTED") != $(readlink -f "$RITZ1") ]]; then
    explode "$WS/projects/ritz/ritz1"
    mkdir -p "$WS/projects/ritz/ritz1/build"
    ln -sfn "$RITZ1" "$WS/$SELFHOSTED"
fi

# The binary --compiler ritz1_selfhosted will execute, by the pipeline's
# own path, must be the file $RITZ1 names.
chosen=$(cd "$WS" && python3 -c '
import sys
from pathlib import Path
sys.path.insert(0, "projects/ritz")
import build_pipeline
print(Path(build_pipeline.RITZ1_SELFHOSTED_BIN).resolve())
')
if [[ $(readlink -f "$RITZ1") != $(readlink -f "$chosen") ]]; then
    echo "rz-builder: RITZ1=$RITZ1 is not the ritz1_selfhosted this workspace runs ($chosen)" >&2
    exit 2
fi
export RITZ1
CACHE_ROOT=${RZ_BUILDER_CACHE:-}
if [[ -n $CACHE_ROOT ]]; then
    if [[ $CACHE_ROOT != /* || ! -d $CACHE_ROOT || ! -w $CACHE_ROOT ]]; then
        echo "rz-builder: RZ_BUILDER_CACHE=$CACHE_ROOT is not a writable absolute directory;" \
            "running uncached" >&2
        CACHE_ROOT=
    fi
fi
if [[ -n $CACHE_ROOT ]]; then
    key=$(cache_key)
    for old in "$CACHE_ROOT"/ritz1-*; do
        if [[ -d $old && $old != "$CACHE_ROOT/$key" ]]; then
            echo "rz-builder: removing $old, the store of another compiler"
            rm -rf "$old"
        fi
    done
    export RITZ_CACHE_DIR=$CACHE_ROOT/$key
    echo "rz-builder: CAS $RITZ_CACHE_DIR ($(find "$RITZ_CACHE_DIR" -name '*.o' 2>/dev/null | wc -l) objects)"
else
    export RITZ_CACHE_DIR=$WS/cas
fi
mkdir -p "$RITZ_CACHE_DIR"
# What the store saved, for summary.json's `cas`; the marker's mtime is the
# run's start, which tells this run's objects from the store's others.
export RITZ_CAS_STATS_LOG=$WS/cas-stats.jsonl
touch "$WS/run-start"
export RITZ_BUILD_CACHE_DIR=$WS/bcache
export PYTHONUNBUFFERED=1

cd "$WS"
set +e
./rz build "$REL" --compiler ritz1_selfhosted 2>&1 | tee "$OUT/build.log"
build_rc=${PIPESTATUS[0]}
test_rc=0
if [[ $BUILD_ONLY -eq 0 && $build_rc -eq 0 ]]; then
    ./rz test "$REL" --compiler ritz1_selfhosted 2>&1 | tee "$OUT/test.log"
    test_rc=${PIPESTATUS[0]}
else
    : > "$OUT/test.log"
fi
set -e

set +e
python3 "$SUMMARY" finish \
    --out "$OUT" \
    --build-log "$OUT/build.log" \
    --build-rc "$build_rc" \
    --test-log "$OUT/test.log" \
    --test-rc "$test_rc" \
    --build-only "$BUILD_ONLY" \
    --package-build "$WS/$REL/build" \
    --cas "$RITZ_CACHE_DIR" \
    --since "$WS/run-start" \
    --cas-stats "$RITZ_CAS_STATS_LOG" \
    --source "$PKG_ARG" \
    --manifest "$WS/$REL/ritz.toml" \
    --ritz1 "$RITZ1"
verdict=$?
cp "$RITZ_CAS_STATS_LOG" "$OUT/cas-stats.jsonl" 2>/dev/null || true
if [[ -n $CACHE_ROOT ]]; then
    python3 "$WS/projects/ritz/cas.py" gc --max-bytes "${RZ_BUILDER_CACHE_MAX_BYTES:-1536MiB}" \
        | tail -1 || echo "rz-builder: trimming $RITZ_CACHE_DIR failed; the verdict stands" >&2
fi
set -e

# /out is a host mount. Files created as root stay root-owned, and the host
# user then cannot remove them (test.sh's cleanup would fail the run). Hand
# the tree back to whoever owns the mount.
if [[ $(id -u) -eq 0 ]]; then
    out_uid=$(stat -c %u "$OUT")
    out_gid=$(stat -c %g "$OUT")
    if [[ $out_uid -ne 0 ]]; then
        chown -R "$out_uid:$out_gid" "$OUT" || true
    fi
    # The same for a mounted cache, which the host saves and restores.
    if [[ -n $CACHE_ROOT && $(stat -c %u "$CACHE_ROOT") -ne 0 ]]; then
        chown -R "$(stat -c %u:%g "$CACHE_ROOT")" "$CACHE_ROOT" || true
    fi
fi
exit "$verdict"
