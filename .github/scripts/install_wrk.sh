#!/usr/bin/env bash
# Install wrk for smoke_stack's stack.wrk_index (AGAST #2464), surviving a
# few minutes of mirror trouble (AGAST #2743).
#
# GitHub's runners lost DNS for archive.ubuntu.com three build-all runs in a
# row; the old one-liner `apt-get install || (update && install)` gave up
# after one blip and turned build-all red with nothing wrong in the code.
#
# Why retries and not a cached .deb or a pinned release: the failures were
# transient DNS, which retrying fixes with no new moving parts. A cache adds
# keys and a dpkg path that runs only when apt is down, i.e. almost never
# tested; building wrk from source adds a toolchain and minutes per run.
#
# Never skips: if wrk still isn't installed after every attempt, this exits
# 1 with a ::error annotation saying why, so build-all fails rather than the
# smoke stack quietly running without its wrk check.
#
# Knobs (tests set them; CI uses the defaults):
#   WRK_INSTALL_ATTEMPTS  tries in total                       (default 5)
#   WRK_INSTALL_BACKOFF   seconds before the 2nd try, doubling (default 15)
# Defaults: waits of 15+30+60+120 s, under 4 minutes before giving up.
set -uo pipefail

attempts=${WRK_INSTALL_ATTEMPTS:-5}
backoff=${WRK_INSTALL_BACKOFF:-15}

if command -v wrk >/dev/null 2>&1; then
    echo "wrk already installed: $(command -v wrk)"
    exit 0
fi

# apt's own per-fetch retries and timeouts first; our loop is for outages
# longer than those cover.
APT_OPTS=(-o Acquire::Retries=3 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30)
export DEBIAN_FRONTEND=noninteractive

delay=$backoff
for ((i = 1; i <= attempts; i++)); do
    echo "install_wrk: attempt $i/$attempts"
    # The first try uses the runner image's package lists (the fast path).
    # A retry refreshes them first: stale lists 404 rather than resolve.
    if ((i > 1)); then
        sudo apt-get "${APT_OPTS[@]}" update ||
            echo "install_wrk: apt-get update failed (attempt $i); trying the install anyway"
    fi
    if sudo apt-get "${APT_OPTS[@]}" install -y wrk && command -v wrk >/dev/null 2>&1; then
        echo "install_wrk: installed $(command -v wrk) on attempt $i"
        wrk --version 2>&1 | head -n 1 || true  # wrk -v exits 1; info only
        exit 0
    fi
    if ((i < attempts)); then
        echo "install_wrk: attempt $i failed; retrying in ${delay}s"
        sleep "$delay"
        delay=$((delay * 2))
    fi
done

echo "::error title=wrk install failed::Could not install wrk after $attempts attempts" \
     "(see apt-get's errors above; usually the Ubuntu mirrors being unreachable)." \
     "The smoke stack's stack.wrk_index check needs wrk, so build-all fails here" \
     "rather than run the smoke stack without it. Re-run the job once the mirrors are back."
exit 1
