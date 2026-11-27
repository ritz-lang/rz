#!/usr/bin/env bash
# Build the packages in indium's initramfs and stage their ELFs in one
# directory (AGAST #2759, #4834): the one implementation of initramfs.pkgs,
# shared by indium's Makefile, tools/mkiso.sh and harland's boot scripts.
#
#   stage_initramfs.sh [--no-build] [--check-compiler NAME] <bin-dir>
#   stage_initramfs.sh --build-only
#   stage_initramfs.sh --list
#
# initramfs.pkgs: one package per line, `#` starts a comment, then optional
# fields:
#
#   compiler=ritz1_selfhosted  build it with the builder image's
#                              ritz1_selfhosted (projects/builder), whatever
#                              the default compiler: the package builds with
#                              that compiler only (Buddhafinger, #4813). The
#                              image comes from projects/builder/
#                              resolve_image.sh (local, ghcr, or built: the
#                              compiler bootstrap is the image's, never
#                              staging's). The run goes to
#                              <pkg>/build/builder/ (the image's /out).
#   bin=SRC[:DEST]             stage only these ELFs, SRC.elf as DEST.elf
#                              (/bin/DEST); repeatable. Without it, every
#                              build/debug/*.elf of the package.
#
# The bin-dir is emptied first. Each staged ELF keeps its build manifest
# beside it (DEST.elf.manifest.json; mkinitramfs.py packs *.elf only).
#
#   --no-build       stage what is already built (the boot scripts'
#                    SKIP_BUILD=1); a package with nothing built is skipped
#                    with a note instead of failing
#   --check-compiler NAME
#                    every staged ELF's manifest must name NAME, or its
#                    entry's compiler= (test_tier1_boot.sh's COMPILER); a
#                    compiler= entry's manifest is checked against it always
#   --build-only     build every package, stage nothing: a boot script
#                    builds before its checks and stages (--no-build) into
#                    its work dir later
#   --list           print each entry's package name, one per line
#
# Environment: COMPILER, the compiler for entries without compiler= (unset:
# rz's default); RZ_CLI (default <repo>/rz) and PKGS_ROOT (default
# <repo>/projects), which tools/test_harland_userland.py points at fakes;
# RZ_BUILDER_IMAGE, the image to use (default: projects/builder/
# resolve_image.sh's); RZ_BUILDER_RUN (default .github/scripts/
# run_builder_package.sh, from the repo root), the
# command that runs one package in the image; RZ_BUILDER_CAS (default
# ${XDG_CACHE_HOME:-~/.cache}/rz-builder-cas), its persistent CAS (#4857).
#
# Exit: 0 staged; 1 a build failed, a package built no ELF, a named bin is
# missing, a manifest names the wrong compiler, or a bad entry; 2 usage;
# 3 a toolchain binary or docker is missing (a SETUP ERROR).

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INDIUM_DIR="$(dirname "$SCRIPT_DIR")"
PROJECTS_DIR="$(dirname "$INDIUM_DIR")"
ROOT_DIR="$(dirname "$PROJECTS_DIR")"
PKGS_FILE="$INDIUM_DIR/initramfs.pkgs"
RZ_CLI="${RZ_CLI:-$ROOT_DIR/rz}"
PKGS_ROOT="${PKGS_ROOT:-$PROJECTS_DIR}"
EXIT_SETUP=3

usage() { echo "usage: stage_initramfs.sh [--no-build] [--check-compiler NAME] <bin-dir> | --build-only | --list" >&2; exit 2; }

build=1 stage_out=1 check="" list=0 bin_dir=""
while [ $# -gt 0 ]; do
    case "$1" in
        --no-build) build=0; shift ;;
        --check-compiler) [ $# -ge 2 ] || usage; check="$2"; shift 2 ;;
        --build-only) stage_out=0; shift ;;
        --list) list=1; shift ;;
        -*) usage ;;
        *) [ -z "$bin_dir" ] || usage; bin_dir="$1"; shift ;;
    esac
done
if [ "$stage_out" -eq 0 ]; then
    [ -z "$bin_dir" ] && [ "$build" -eq 1 ] && [ -z "$check" ] || usage
elif [ "$list" -eq 0 ]; then
    [ -n "$bin_dir" ] || usage
fi

# The entries, comments stripped: "pkg field field ..." per line.
mapfile -t ENTRIES < <(sed -e 's/#.*//' "$PKGS_FILE" | awk 'NF')
[ "${#ENTRIES[@]}" -gt 0 ] || { echo "FAIL: no packages in $PKGS_FILE"; exit 1; }

if [ "$list" -eq 1 ]; then
    for e in "${ENTRIES[@]}"; do set -- $e; echo "$1"; done
    exit 0
fi

if [ "$stage_out" -eq 1 ]; then
    rm -rf "$bin_dir" && mkdir -p "$bin_dir" || { echo "FAIL: can't create $bin_dir"; exit 1; }
fi

# manifest_compiler FILE: the compiler a build manifest names, or "".
manifest_compiler() {
    python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("compiler", ""))' "$1" 2>/dev/null
}

# stage SRC_ELF DEST_NAME WANT: copy one ELF (and its manifest) in; WANT is
# the compiler --check-compiler requires of it.
stage() {
    local src="$1" dest="$bin_dir/$2.elf" want="$3"
    cp "$src" "$dest" || return 1
    [ -f "$src.manifest.json" ] && cp "$src.manifest.json" "$dest.manifest.json"
    if [ -n "$want" ]; then
        [ -f "$dest.manifest.json" ] || { echo "FAIL: $(basename "$src") has no build manifest ($src.manifest.json)"; return 1; }
        local by
        by="$(manifest_compiler "$dest.manifest.json")"
        [ "$by" = "$want" ] || { echo "FAIL: $(basename "$src") was built by ${by:-an unknown compiler}, not $want"; return 1; }
    fi
}

rc=0
for e in "${ENTRIES[@]}"; do
    set -- $e
    pkg="$1"; shift
    pin="" bins=()
    for f in "$@"; do
        case "$f" in
            compiler=ritz1_selfhosted) pin="${f#compiler=}" ;;
            compiler=*) echo "FAIL: $pkg: $f: only compiler=ritz1_selfhosted (the builder image's) can be pinned"; exit 1 ;;
            bin=?*) bins+=("${f#bin=}") ;;
            *) echo "FAIL: $pkg: unknown field '$f' in $PKGS_FILE"; exit 1 ;;
        esac
    done
    # A pinned entry's manifest must always name its pin: the stale
    # build/debug of a default-compiler build must never pass as it.
    want="${pin:-$check}"

    if [ -n "$pin" ]; then
        # The image's /out: build/<profile>/ is the package build tree.
        out_dir="$PKGS_ROOT/$pkg/build/builder"
        debug_dir="$out_dir/build/debug"
        if [ "$build" -eq 1 ]; then
            if [ -n "${RZ_BUILDER_IMAGE:-}" ]; then
                image="$RZ_BUILDER_IMAGE" irc=0
            else
                image="$(bash "$ROOT_DIR/projects/builder/resolve_image.sh")"
                irc=$?
            fi
            [ "$irc" -eq "$EXIT_SETUP" ] && exit "$EXIT_SETUP"
            [ "$irc" -eq 0 ] || { echo "FAIL: no builder image for $pkg"; exit 1; }
            echo "=== Building $pkg with $pin in $image ==="
            rm -rf "$out_dir"
            cas="${RZ_BUILDER_CAS:-${XDG_CACHE_HOME:-$HOME/.cache}/rz-builder-cas}"
            (cd "$ROOT_DIR" && ${RZ_BUILDER_RUN:-bash .github/scripts/run_builder_package.sh} \
                --build-only --cache "$cas" "$image" "projects/$pkg" "$out_dir") \
                || { echo "FAIL: build of $pkg in the builder image failed"; exit 1; }
        fi
    else
        debug_dir="$PKGS_ROOT/$pkg/build/debug"
        if [ "$build" -eq 1 ]; then
            echo "=== Building $pkg ==="
            "$RZ_CLI" build "$pkg" ${COMPILER:+--compiler "$COMPILER"}
            brc=$?
            [ "$brc" -eq "$EXIT_SETUP" ] && { echo "SETUP ERROR: build of $pkg: a toolchain binary is missing" >&2; exit "$EXIT_SETUP"; }
            [ "$brc" -eq 0 ] || { echo "FAIL: build of $pkg failed"; exit 1; }
        fi
    fi

    [ "$stage_out" -eq 1 ] || continue
    if [ "${#bins[@]}" -eq 0 ]; then
        elfs=("$debug_dir"/*.elf)
        if [ ! -f "${elfs[0]}" ]; then
            [ "$build" -eq 0 ] && { echo "note: $pkg: nothing built in $debug_dir; not staged"; continue; }
            echo "FAIL: $pkg built no ELFs"; exit 1
        fi
        for f in "${elfs[@]}"; do
            stage "$f" "$(basename "$f" .elf)" "$want" || rc=1
        done
    else
        for b in "${bins[@]}"; do
            src="${b%%:*}" dest="${b#*:}"
            if [ ! -f "$debug_dir/$src.elf" ]; then
                [ "$build" -eq 0 ] && { echo "note: $pkg: $src.elf not built in $debug_dir; not staged"; continue; }
                echo "FAIL: $pkg built no $src.elf"; exit 1
            fi
            stage "$debug_dir/$src.elf" "$dest" "$want" || rc=1
        done
    fi
done
exit "$rc"
