#!/usr/bin/env python3
"""
Create an initramfs TAR image for Harland.

Creates a TAR archive containing:
- /bin/* - User programs
- /etc/* - Configuration files
"""

import argparse
import os
import tarfile
import tempfile
import subprocess
from pathlib import Path


def create_initramfs(bin_dir: Path, output: Path, extra_files: dict = None):
    """Create an initramfs TAR archive.

    Args:
        bin_dir: Directory containing user ELF binaries
        output: Output TAR file path (or qcow2 if write_to_disk is True)
        extra_files: Dict of {path: content} for additional files
    """
    print(f"Creating initramfs: {output}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tar_path = tmpdir / "initramfs.tar"

        # Create TAR archive (USTAR format, no PAX headers)
        with tarfile.open(tar_path, "w", format=tarfile.USTAR_FORMAT) as tar:
            # Add /etc directory structure
            print("  Adding /etc...")

            # /etc/hostname
            hostname_path = tmpdir / "hostname"
            hostname_path.write_text("harland\n")
            tar.add(str(hostname_path), arcname="./etc/hostname")

            # /etc/motd
            motd_path = tmpdir / "motd"
            motd_path.write_text("""Welcome to Harland!
Goliath filesystem initialized.
""")
            tar.add(str(motd_path), arcname="./etc/motd")

            # Add user binaries
            if bin_dir.exists():
                print(f"  Adding binaries from {bin_dir}...")
                for elf in sorted(bin_dir.glob("*.elf")):
                    if elf.name == "harland.elf":
                        continue  # Skip kernel
                    # Remove .elf extension for /bin name
                    bin_name = elf.stem
                    print(f"    /bin/{bin_name}")
                    tar.add(str(elf), arcname=f"./bin/{bin_name}")

            # Add any extra files
            if extra_files:
                for path, content in extra_files.items():
                    extra_path = tmpdir / "extra"
                    extra_path.write_text(content)
                    tar.add(str(extra_path), arcname=f".{path}")

        # Check output type
        if output.suffix == ".qcow2":
            # Write TAR to qcow2 image
            print(f"  Writing to QCOW2 image...")

            # Create raw image from TAR
            tar_size = tar_path.stat().st_size
            # Round up to 1MB boundary
            image_size = ((tar_size + 1024*1024 - 1) // (1024*1024)) * 1024*1024
            image_size = max(image_size, 64 * 1024 * 1024)  # Minimum 64MB

            raw_path = tmpdir / "initramfs.raw"

            # Create raw image with TAR contents
            with open(raw_path, "wb") as f:
                with open(tar_path, "rb") as tar_file:
                    f.write(tar_file.read())
                # Pad to image_size
                f.truncate(image_size)

            # Convert to QCOW2
            subprocess.run([
                "qemu-img", "convert", "-f", "raw", "-O", "qcow2",
                str(raw_path), str(output)
            ], check=True)
        else:
            # Just copy the TAR file
            import shutil
            shutil.copy(tar_path, output)

        # Print stats
        tar_size = tar_path.stat().st_size
        print(f"  TAR size: {tar_size} bytes ({tar_size // 1024} KB)")

    print(f"  Created: {output}")


def main():
    parser = argparse.ArgumentParser(description="Create initramfs for Harland")
    parser.add_argument("--bin-dir", type=Path, required=True,
                        help="Directory containing user ELF binaries")
    parser.add_argument("--output", type=Path, required=True,
                        help="Output file (.tar or .qcow2)")

    args = parser.parse_args()

    create_initramfs(args.bin_dir, args.output)
    return 0


if __name__ == "__main__":
    exit(main())
