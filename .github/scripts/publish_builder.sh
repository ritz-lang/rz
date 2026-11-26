#!/usr/bin/env bash
# Tag and push the builder image that projects/builder/test.sh built and
# tested (AGAST #4824).  .github/workflows/builder.yml runs it.
#
#   publish_builder.sh [--dry-run] <commit> <image> <ref>
#
#   <commit>  the full 40-hex rz commit the image was built from
#   <image>   the registry repository, no tag (ghcr.io/ritz-lang/rz-builder)
#   <ref>     the git ref the run is for (GITHUB_REF): refs/heads/<b> or
#             refs/tags/<t>
#
# It finds the one local `rz-builder:*` image labelled
# dev.ritz.rz.commit=<commit> (test.sh --keep leaves it), reads the
# ritz1_selfhosted sha256 from its dev.ritz.ritz1-selfhosted.sha256 label, and
# pushes it as
#
#   refs/tags/<t>     <image>:<t'>  <image>:ritz1-<sha256[:12]>  <image>:<commit>
#   refs/heads/main   <image>:main  <image>:<commit>
#   any other branch  nothing (a dry run names <image>:<commit> only)
#
# <t'> is the git tag as a Docker tag: each byte outside [A-Za-z0-9_.-]
# becomes '-', a leading '.' or '-' becomes '_', and it is cut to 128
# characters.  A tag that comes out as `main`, `ritz1-*` or a 40-hex commit
# is refused: those tags are this script's, and a git tag must not move them.
#
# --dry-run prints the tags and pushes nothing; the workflow runs that on
# every run.  Without --dry-run, inside Actions (GITHUB_ACTIONS=true) it
# refuses anything but a push event for <ref> itself, under the job's own
# `if:`.  Login is the job's business, not this script's: it never sees a
# credential.
#
# Exit: 0 pushed (or would have), 1 no unique labelled image or not a
# publishing push, 2 bad arguments.
set -euo pipefail
export LC_ALL=C   # the sanitiser's character class is per byte

dry=0
if [[ "${1:-}" == "--dry-run" ]]; then dry=1; shift; fi
if [[ $# -ne 3 ]]; then
    echo "usage: publish_builder.sh [--dry-run] <commit> <image> <ref>" >&2; exit 2
fi
commit="$1" image="$2" ref="$3"
if [[ ! "$commit" =~ ^[0-9a-f]{40}$ ]]; then
    echo "publish_builder: '$commit' is not a full 40-hex commit" >&2; exit 2
fi
# A ':' after the last '/' is a tag (a registry host may carry a port).
if [[ "${image##*/}" == *:* || "$image" == *@* || -z "$image" ]]; then
    echo "publish_builder: give the image without a tag or digest: '$image'" >&2; exit 2
fi

# The git tag as a Docker tag ([A-Za-z0-9_][A-Za-z0-9_.-]{0,127}).
docker_tag() {
    local t="${1//[^A-Za-z0-9_.-]/-}"
    [[ "$t" == [.-]* ]] && t="_${t:1}"
    printf '%s' "${t:0:128}"
}

publishable=1
case "$ref" in
refs/tags/*)
    git_tag="${ref#refs/tags/}"
    if [[ -z "$git_tag" ]]; then
        echo "publish_builder: '$ref' names an empty tag" >&2; exit 2
    fi
    tag="$(docker_tag "$git_tag")"
    if [[ "$tag" == main || "$tag" == ritz1-* || "$tag" =~ ^[0-9a-f]{40}$ ]]; then
        echo "publish_builder: git tag '$git_tag' becomes :$tag, which is reserved for the workflow's own tags (main, ritz1-*, <commit>)" >&2
        exit 2
    fi
    kind=tag ;;
refs/heads/main) kind=main ;;
refs/heads/?*)   kind=branch publishable=0 ;;
*)
    echo "publish_builder: '$ref' is not a branch or tag ref (refs/heads/... or refs/tags/...)" >&2
    exit 2 ;;
esac

if [[ $dry -eq 0 ]]; then
    if [[ $publishable -eq 0 ]]; then
        echo "publish_builder: only a push to main or a tag publishes, not $ref" >&2; exit 1
    fi
    if [[ "${GITHUB_ACTIONS:-}" == "true" ]] &&
       [[ "${GITHUB_EVENT_NAME:-}" != "push" || "${GITHUB_REF:-}" != "$ref" ]]; then
        echo "publish_builder: only a push of $ref publishes it (this is ${GITHUB_EVENT_NAME:-?} on ${GITHUB_REF:-?})" >&2
        exit 1
    fi
fi

mapfile -t found < <(docker image ls --filter "label=dev.ritz.rz.commit=$commit" \
    --filter "reference=rz-builder:*" --format '{{.Repository}}:{{.Tag}}' | sort -u)
if [[ ${#found[@]} -ne 1 ]]; then
    echo "publish_builder: want one rz-builder image labelled with ${commit:0:12}, found ${#found[@]} rz-builder images: ${found[*]:-none}" >&2
    [[ ${#found[@]} -eq 0 ]] && echo "publish_builder: no rz-builder image (did test.sh run with --keep?)" >&2
    exit 1
fi
src="${found[0]}"
sha="$(docker image inspect "$src" --format '{{ index .Config.Labels "dev.ritz.ritz1-selfhosted.sha256" }}')"
if [[ ! "$sha" =~ ^[0-9a-f]{64}$ ]]; then
    echo "publish_builder: $src's ritz1_selfhosted sha256 label is '$sha'" >&2; exit 1
fi

case "$kind" in
tag)    tags=("$image:$tag" "$image:ritz1-${sha:0:12}" "$image:$commit") ;;
main)   tags=("$image:main" "$image:$commit") ;;
branch) tags=("$image:$commit") ;;
esac
if [[ $dry -eq 1 ]]; then
    for t in "${tags[@]}"; do echo "would push $t (from $src)"; done
    [[ $publishable -eq 0 ]] && echo "$ref publishes nothing: only a push to main or a tag does"
else
    for t in "${tags[@]}"; do docker tag "$src" "$t"; done
    for t in "${tags[@]}"; do docker push "$t"; echo "pushed $t"; done
fi

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
        echo "### builder image ${commit:0:12} ($ref)"
        echo
        echo "ritz1_selfhosted sha256 \`$sha\`"
        echo
        [[ $dry -eq 1 ]] && echo "Tags (dry run, nothing pushed):" || echo "Pushed:"
        for t in "${tags[@]}"; do echo "- \`$t\`"; done
    } >> "$GITHUB_STEP_SUMMARY"
fi
