#!/usr/bin/env bash
# Install what projects/harland/tools/test_tier1_boot.sh needs to boot
# harland under OVMF on an ubuntu-latest runner (AGAST #1845):
#
#   qemu-system-x86     qemu-system-x86_64
#   qemu-utils          qemu-img (each boot's qcow2 overlay)
#   ovmf                /usr/share/OVMF/OVMF_CODE_4M.fd + VARS
#   grub-efi-amd64-bin  /usr/lib/grub/x86_64-efi (+ grub-mkstandalone via
#                       its grub-common dependency)
#
# --no-install-recommends (AGAST #4222): Recommends pulled 86 packages /
# 46.6 MB onto the ubuntu-26.04 runner (gstreamer, pipewire, sdl2, spice,
# vte, qemu-system-gui...); without them it is 17 packages / ~26 MB. The
# boot runs -display none, and ipxe-qemu (the default NIC's option ROMs) is
# a hard Depends of qemu-system-x86, so nothing the boot uses is lost.
#
# Each attempt first fetches with --download-only under
# BOOT_TOOLS_FETCH_TIMEOUT: killing a fetch is harmless and apt resumes the
# partial file next attempt, so a ~75 kB/s mirror (2026-11-18, runs
# 44398657610 and 44416492749) still finishes inside the step. Only a
# completed fetch is installed, so dpkg is never killed half way. Defaults
# keep every attempt + backoff inside the step's 10 minutes
# (test_install_boot_tools.py checks), so a dead mirror ends in the
# ::error below, not a bare step timeout.
#
# BOOT_TOOLS_DEB_CACHE=DIR keeps the .debs in DIR, which main.yml restores
# and saves with actions/cache: a warm run downloads nothing.
#
# Knobs: BOOT_TOOLS_INSTALL_ATTEMPTS (default 3), BOOT_TOOLS_INSTALL_BACKOFF
# (seconds before the 2nd try, doubling; default 10), BOOT_TOOLS_FETCH_TIMEOUT
# (seconds per fetch; default 150), BOOT_TOOLS_DEB_CACHE (unset: apt's own).
# BOOT_TOOLS_GRUB_DIR / BOOT_TOOLS_OVMF_DIR move have_tools()'s two absolute
# paths for the self-tests only.
set -uo pipefail

PACKAGES=(qemu-system-x86 qemu-utils ovmf grub-efi-amd64-bin)
attempts=${BOOT_TOOLS_INSTALL_ATTEMPTS:-3}
backoff=${BOOT_TOOLS_INSTALL_BACKOFF:-10}
fetch_timeout=${BOOT_TOOLS_FETCH_TIMEOUT:-150}
cache=${BOOT_TOOLS_DEB_CACHE:-}
cache=${cache/#\~/$HOME} # main.yml's env: value is the cache step's ~/ path, unexpanded
grub_dir=${BOOT_TOOLS_GRUB_DIR:-/usr/lib/grub/x86_64-efi}
ovmf_dir=${BOOT_TOOLS_OVMF_DIR:-/usr/share/OVMF}

# Exactly the setup checks test_tier1_boot.sh makes.
have_tools() {
    command -v qemu-system-x86_64 >/dev/null &&
        command -v qemu-img >/dev/null &&
        command -v grub-mkstandalone >/dev/null &&
        [ -d "$grub_dir" ] &&
        ls "$ovmf_dir"/OVMF_CODE*.fd >/dev/null 2>&1
}

if have_tools; then
    echo "install_boot_tools: already installed"
    exit 0
fi

APT_OPTS=(-o Acquire::Retries=3 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30
          -o APT::Keep-Downloaded-Packages=true)
if [ -n "$cache" ]; then
    mkdir -p "$cache"
    APT_OPTS+=(-o "Dir::Cache::Archives=$cache")
    echo "install_boot_tools: .deb cache $cache ($(ls "$cache"/*.deb 2>/dev/null | wc -l) cached)"
fi
INSTALL=(install -y --no-install-recommends)
export DEBIAN_FRONTEND=noninteractive

# Hand the cache back to the runner user for actions/cache's save: drop
# apt's root-only partial/ dir and lock, and the .debs no mirror serves now.
save_cache() {
    [ -n "$cache" ] || return 0
    sudo apt-get "${APT_OPTS[@]}" autoclean >/dev/null ||
        echo "install_boot_tools: autoclean failed; saving the cache as is"
    sudo rm -rf "$cache/partial" "$cache/lock"
    sudo chown -R "$(id -u):$(id -g)" "$cache"
}

delay=$backoff
for ((i = 1; i <= attempts; i++)); do
    echo "install_boot_tools: attempt $i/$attempts"
    if ((i > 1)); then
        sudo apt-get "${APT_OPTS[@]}" update ||
            echo "install_boot_tools: apt-get update failed (attempt $i); trying the fetch anyway"
    fi
    timeout -k 10 "$fetch_timeout" \
        sudo apt-get "${APT_OPTS[@]}" "${INSTALL[@]}" --download-only "${PACKAGES[@]}"
    rc=$?
    if ((rc == 0)); then
        if sudo apt-get "${APT_OPTS[@]}" "${INSTALL[@]}" "${PACKAGES[@]}" && have_tools; then
            echo "install_boot_tools: installed on attempt $i"
            qemu-system-x86_64 --version | head -n 1
            save_cache
            exit 0
        fi
        echo "install_boot_tools: install failed (attempt $i)"
    elif ((rc == 124 || rc == 137)); then
        echo "install_boot_tools: fetch timed out after ${fetch_timeout}s (attempt $i); the next attempt resumes it"
    else
        echo "install_boot_tools: fetch failed with exit $rc (attempt $i)"
    fi
    if ((i < attempts)); then
        echo "install_boot_tools: retrying in ${delay}s"
        sleep "$delay"
        delay=$((delay * 2))
    fi
done

echo "::error title=boot tools install failed::Could not install ${PACKAGES[*]}" \
     "after $attempts attempts (see apt-get's errors above). The harland boot" \
     "needs them, so build-all fails here rather than skip the boot."
exit 1
