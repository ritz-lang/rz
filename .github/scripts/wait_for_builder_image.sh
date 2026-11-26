#!/bin/sh
# Wait until <image>:<commit> is in its registry (AGAST #4846).
#
#   wait_for_builder_image.sh <image> <commit>
#
#   <image>   the repository, no tag: ghcr.io/ritz-lang/rz-builder
#   <commit>  the full 40-hex commit; the tag main.yml's builder-image job
#             publishes for a push to main
#
# .woodpecker/builder.yml's first step. Every later step's pod runs
# <image>:<commit> as its image, and Woodpecker's kubernetes backend fails a
# step the moment its pod can't pull (ImagePullBackOff), so the pipeline
# waits here first: main.yml's gitea-push can land, and Woodpecker start, before
# GitHub has built and pushed the image (~5 min after the push).
#
# Anonymous: ghcr hands a pull token for a public package to anyone. POSIX
# sh and curl only (the step's image is curlimages/curl).
#
#   WAIT_TIMEOUT   seconds before giving up (default 2400)
#   WAIT_INTERVAL  seconds between polls (default 30)
#
# Exit: 0 the tag exists; 1 it didn't appear in time; 2 bad arguments.
set -eu

usage() {
    echo "usage: wait_for_builder_image.sh <image> <commit>" >&2
    exit 2
}
[ $# -eq 2 ] || usage
image=$1 commit=$2
case $commit in
*[!0-9a-f]*|'') usage ;;
esac
[ ${#commit} -eq 40 ] || usage
case ${image##*/} in
*:*|*@*) echo "wait_for_builder_image: give the image without a tag: $image" >&2; usage ;;
esac
case $image in
*/*) ;;
*) usage ;;
esac

registry=${image%%/*}
repo=${image#*/}
timeout=${WAIT_TIMEOUT:-2400}
interval=${WAIT_INTERVAL:-30}
accept='application/vnd.oci.image.index.v1+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.docker.distribution.manifest.v2+json'

start=$(date +%s)
while :; do
    token=$(curl -fsS "https://$registry/token?scope=repository:$repo:pull&service=$registry" |
        sed -n 's/.*"token" *: *"\([^"]*\)".*/\1/p') || token=
    code=$(curl -sS -o /dev/null -w '%{http_code}' -I \
        -H "Authorization: Bearer $token" -H "Accept: $accept" \
        "https://$registry/v2/$repo/manifests/$commit") || code=000
    if [ "$code" = 200 ]; then
        echo "wait_for_builder_image: $image:$commit is published"
        exit 0
    fi
    now=$(date +%s)
    if [ $((now - start)) -ge "$timeout" ]; then
        echo "wait_for_builder_image: $image:$commit not published after ${timeout}s (last HTTP $code); did main.yml's builder-image job fail?" >&2
        exit 1
    fi
    echo "wait_for_builder_image: $image:$commit not there yet (HTTP $code)"
    sleep "$interval"
done
