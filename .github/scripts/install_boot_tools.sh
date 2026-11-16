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
# Recommends stay on: qemu-system-x86 recommends ipxe-qemu, whose option
# ROMs back the default NIC the boot script does not turn off.
#
# Same shape as install_wrk.sh (AGAST #2743): retry update+install with
# backoff through mirror trouble, then fail loudly if a tool is still
# missing, so the boot never runs without them and reads as a SETUP ERROR.
#
# Knobs: BOOT_TOOLS_INSTALL_ATTEMPTS (default 5), BOOT_TOOLS_INSTALL_BACKOFF
# (seconds before the 2nd try, doubling; default 15).
set -uo pipefail

PACKAGES=(qemu-system-x86 qemu-utils ovmf grub-efi-amd64-bin)
attempts=${BOOT_TOOLS_INSTALL_ATTEMPTS:-5}
backoff=${BOOT_TOOLS_INSTALL_BACKOFF:-15}

# Exactly the setup checks test_tier1_boot.sh makes.
have_tools() {
    command -v qemu-system-x86_64 >/dev/null &&
        command -v qemu-img >/dev/null &&
        command -v grub-mkstandalone >/dev/null &&
        [ -d /usr/lib/grub/x86_64-efi ] &&
        ls /usr/share/OVMF/OVMF_CODE*.fd >/dev/null 2>&1
}

if have_tools; then
    echo "install_boot_tools: already installed"
    exit 0
fi

APT_OPTS=(-o Acquire::Retries=3 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30)
export DEBIAN_FRONTEND=noninteractive

delay=$backoff
for ((i = 1; i <= attempts; i++)); do
    echo "install_boot_tools: attempt $i/$attempts"
    if ((i > 1)); then
        sudo apt-get "${APT_OPTS[@]}" update ||
            echo "install_boot_tools: apt-get update failed (attempt $i); trying the install anyway"
    fi
    if sudo apt-get "${APT_OPTS[@]}" install -y "${PACKAGES[@]}" && have_tools; then
        echo "install_boot_tools: installed on attempt $i"
        qemu-system-x86_64 --version | head -n 1
        exit 0
    fi
    if ((i < attempts)); then
        echo "install_boot_tools: attempt $i failed; retrying in ${delay}s"
        sleep "$delay"
        delay=$((delay * 2))
    fi
done

echo "::error title=boot tools install failed::Could not install ${PACKAGES[*]}" \
     "after $attempts attempts (see apt-get's errors above). The harland boot" \
     "needs them, so build-all fails here rather than skip the boot."
exit 1
