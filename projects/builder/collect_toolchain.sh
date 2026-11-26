#!/usr/bin/env bash
# Copy the native tools a build calls, and the shared libraries they load,
# into <dest> at their own paths (AGAST #4822).
#
#   bash projects/builder/collect_toolchain.sh <dest> <tool>...
#
# The Dockerfile's bootstrap stage runs this with the tools the survey found
# (projects/builder/README.md, "Native tools") and the runtime stage copies
# <dest> over /.  The clang-21 package alone would bring ~460 MB of
# dependencies a Ritz build never touches (libc6-dev, libstdc++-dev, gcc's
# sanitizer runtimes); this copies the executables and their ldd closure.
#
# A symlink is copied as a symlink, with every link in its chain and the
# file it ends at, so ld.lld -> lld and as -> x86_64-linux-gnu-as keep
# working.  Libraries from libc6 are skipped: the runtime stage's base image
# is the same Debian image and has them.
set -euo pipefail

dest="$1"; shift
[[ $# -gt 0 ]] || { echo "usage: collect_toolchain.sh <dest> <tool>..." >&2; exit 2; }
mkdir -p "$dest"

# usr_path <path>: the /usr spelling of a merged-/usr path.  ldd says
# /lib/x86_64-linux-gnu/...; `cp --parents` would make <dest>/lib a real
# directory, and copying that over the runtime's /lib -> usr/lib symlink
# would replace it.
usr_path() {
    case "$1" in
        /lib/*|/lib64/*|/bin/*|/sbin/*) echo "/usr$1" ;;
        *) echo "$1" ;;
    esac
}

# copy_chain <path>: the path, each symlink it passes through, and the file.
copy_chain() {
    local p t
    p="$(usr_path "$1")"
    while :; do
        cp -a --parents "$p" "$dest"
        [[ -L "$p" ]] || break
        t="$(readlink "$p")"
        [[ "$t" == /* ]] || t="$(dirname "$p")/$t"
        p="$(usr_path "$(realpath -s "$t")")"
    done
}

declare -A libs=()
for tool in "$@"; do
    path="$(command -v "$tool")" || { echo "collect_toolchain: $tool not on PATH" >&2; exit 1; }
    copy_chain "$path"
    while read -r lib; do libs[$lib]=1; done < <(ldd "$(realpath "$path")" | awk '$3 ~ /^\// {print $3}')
done

# dpkg lists libc6's files under either spelling, so compare both.
libc_files="$(dpkg -L libc6)"
is_libc() {
    local p
    for p in "$1" "$(realpath "$1")" "$(usr_path "$1")" "${1#/usr}"; do
        grep -qxF "$p" <<<"$libc_files" && return 0
    done
    return 1
}
for lib in "${!libs[@]}"; do
    is_libc "$lib" || copy_chain "$lib"
done
