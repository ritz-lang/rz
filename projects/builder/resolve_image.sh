#!/usr/bin/env bash
# Print a local builder image ref for a commit's compiler sources (AGAST
# #4834), for a host step that wants the image's ritz1_selfhosted rather
# than one of its own: Indium's initramfs staging builds Buddhafinger with
# it (projects/indium/tools/stage_initramfs.sh).
#
#   resolve_image.sh [<commit>]       <commit> defaults to HEAD
#
# The image is keyed by content, not by commit (AGAST #4903):
# projects/ritz/tools/builder_src_key.py hashes what the image's bootstrap
# builds from, so every commit that leaves the compiler alone shares one
# image. In order:
#
#   1. RZ_BUILDER_IMAGE, if set: used as given, never pulled or built;
#   2. rz-builder:src-<key>, if it is already local;
#   3. ghcr.io/ritz-lang/rz-builder:src-<key>, pulled anonymously (main.yml's
#      builder-image job publishes it for main), tagged rz-builder:src-<key>;
#      RZ_BUILDER_NO_PULL=1 skips this;
#   4. built here: the Dockerfile's two passes over `git archive <commit>`,
#      as projects/builder/test.sh builds it, minus test.sh's checks.
#      The compiler bootstrap is the image build's, never the caller's.
#
# The key covers <commit>'s tree, not the work tree: uncommitted compiler
# edits are not in the image. Only the ref goes to stdout; docker's output
# goes to stderr.
#
# Exit: 0 printed a ref; 1 the build failed; 3 docker is missing or its
# daemon does not answer (a SETUP ERROR, as the boot scripts' 3).
set -euo pipefail

if [[ -n ${RZ_BUILDER_IMAGE:-} ]]; then
    echo "$RZ_BUILDER_IMAGE"
    exit 0
fi

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
rev="${1:-HEAD}"

command -v docker >/dev/null || { echo "SETUP ERROR: docker not found (the builder image builds ritz1_selfhosted packages)" >&2; exit 3; }
docker info >/dev/null 2>&1 || { echo "SETUP ERROR: the docker daemon does not answer" >&2; exit 3; }

commit="$(git -C "$ROOT" rev-parse --verify "$rev^{commit}")"
key="$(python3 "$ROOT/projects/ritz/tools/builder_src_key.py" "$commit")"
local_tag="rz-builder:src-$key"

if docker image inspect "$local_tag" >/dev/null 2>&1; then
    echo "$local_tag"
    exit 0
fi

if [[ ${RZ_BUILDER_NO_PULL:-0} != 1 ]]; then
    remote="ghcr.io/ritz-lang/rz-builder:src-$key"
    # Anonymous: the package is public, and a host's credential helper (WSL's
    # docker-credential-desktop.exe) may not run here at all.
    anon="$(mktemp -d)"
    echo '{}' > "$anon/config.json"
    if DOCKER_CONFIG="$anon" docker pull -q "$remote" >&2 2>/dev/null; then
        rm -rf "$anon"
        docker tag "$remote" "$local_tag"
        echo "$local_tag"
        exit 0
    fi
    rm -rf "$anon"
    echo "resolve_image: $remote is not published; building it" >&2
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
git -C "$ROOT" archive --format=tar "$commit" > "$work/context.tar"
build() { docker build -q -f projects/builder/Dockerfile "$@" - < "$work/context.tar" >&2; }
boot_tag="rz-builder-bootstrap:src-$key"
echo "resolve_image: pass 1, the bootstrap (ritz0 -> ritz1 -> ritz1_selfhosted)" >&2
build --target bootstrap -t "$boot_tag" || { echo "resolve_image: the bootstrap stage failed" >&2; exit 1; }
sha="$(docker run --rm "$boot_tag" sha256sum projects/ritz/ritz1/build/ritz1_selfhosted | cut -d' ' -f1)"
echo "resolve_image: pass 2, the runtime image (ritz1_selfhosted $sha)" >&2
build --build-arg "RZ_COMMIT=$commit" --build-arg "RITZ1_SHA256=$sha" -t "$local_tag" \
    || { echo "resolve_image: the runtime stage failed" >&2; exit 1; }
docker image rm "$boot_tag" >/dev/null 2>&1 || true
echo "$local_tag"
