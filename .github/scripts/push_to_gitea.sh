#!/usr/bin/env bash
# Push a commit of main to Gitea (AGAST #4846).
#
#   push_to_gitea.sh <repo-url> <commit>
#
#   <repo-url>  https://git.fucken.ninja/ritz-lang/rz.git (file:// for tests)
#   <commit>    the full 40-hex commit; it becomes refs/heads/main there
#
# main.yml's gitea-push job runs this on every push to main and appends its
# one line, `pushed=true` or `pushed=false`, to $GITHUB_OUTPUT. GitHub stays
# canonical (Aaron, 2026-11-26); the push's webhook starts
# .woodpecker/builder.yml on https://ci.fucken.ninja, and builder-fleet runs
# the hosted matrix unless this said pushed=true.
#
# GITEA_PUSH_TOKEN is a Gitea access token (scope write:repository) of an
# account with write access to the repo. It reaches git only through a
# credential helper that reads it from the environment: never argv, never the
# URL. Gitea takes a token as the basic-auth username with the password
# `x-oauth-basic`.
#
# No force: GitHub's main only moves forward, so a rejected push means Gitea
# has history GitHub doesn't, which a person must look at.
#
# Exit: 0 pushed, or skipped with a warning when GITEA_PUSH_TOKEN is unset or
# empty (the secret isn't configured yet); 1 the push failed; 2 bad arguments.
set -euo pipefail

usage() {
    echo "usage: push_to_gitea.sh <https://...|file://...> <40-hex commit>" >&2
    exit 2
}
[[ $# -eq 2 ]] || usage
url=$1 commit=$2
[[ $url == https://* || $url == file://* ]] || usage
[[ $commit =~ ^[0-9a-f]{40}$ ]] || usage

if [[ -z "${GITEA_PUSH_TOKEN:-}" ]]; then
    echo "::warning::GITEA_PUSH_TOKEN is not set: main not pushed to Gitea, so Woodpecker won't run it (the hosted builder matrix will)" >&2
    echo "pushed=false"
    exit 0
fi

# The helper's text names the variable, not its value. The empty
# credential.helper first drops any helper the runner configured.
# shellcheck disable=SC2016  # expanded by the helper's shell, not this one
helper='!f() { test "$1" = get || exit 0; echo "username=$GITEA_PUSH_TOKEN"; echo "password=x-oauth-basic"; }; f'
export GIT_TERMINAL_PROMPT=0
if ! git -c credential.helper= -c "credential.helper=$helper" \
        push "$url" "$commit:refs/heads/main" >&2; then
    echo "push_to_gitea: pushing $commit to $url main failed" >&2
    exit 1
fi
echo "pushed=true"
