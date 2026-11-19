#!/usr/bin/env python3
"""Upload a raw disk image to a new EBS snapshot with the EBS direct APIs.

AGAST #1849. The old pipeline (iac/deployment) launched a builder instance,
scp'd the image to it, dd'd it onto a volume, stopped the builder and
snapshotted the volume: a second instance and minutes of billing for a 128 MiB
image. The EBS direct APIs write the snapshot from this host instead, and only
the blocks that hold data (an ESP image is mostly zeros) are sent.

Only the `aws` CLI is used (no boto3): `ebs start-snapshot`,
`ebs put-snapshot-block` per non-zero 512 KiB block, `ebs complete-snapshot`,
then `ec2 wait snapshot-completed`.

Usage:
    ebs_snapshot.py upload IMAGE --region R [--tag K=V ...]   # prints the snapshot id
    ebs_snapshot.py plan IMAGE                                # block count, no AWS
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BLOCK = 512 * 1024  # the EBS direct API block size
GIB = 1 << 30


def changed_blocks(data: bytes) -> Iterator[tuple[int, bytes, str]]:
    """(index, block, base64 sha256) for every block that is not all zeros.

    The last block is zero-padded to BLOCK: put-snapshot-block takes whole
    blocks only. Zero blocks are skipped; a new snapshot reads them as zeros.
    """
    zero = bytes(BLOCK)
    for i in range(0, len(data), BLOCK):
        chunk = data[i:i + BLOCK]
        if len(chunk) < BLOCK:
            chunk = chunk + bytes(BLOCK - len(chunk))
        if chunk == zero:
            continue
        digest = base64.b64encode(hashlib.sha256(chunk).digest()).decode()
        yield i // BLOCK, chunk, digest


def volume_gib(nbytes: int) -> int:
    """The snapshot's volume size: whole GiB, at least 1."""
    return max(1, -(-nbytes // GIB))


def _aws(region: str, *args: str) -> str:
    cmd = ["aws", "--region", region, "--output", "json", *args]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"aws {' '.join(args[:2])} failed ({p.returncode}): {p.stderr.strip()}")
    return p.stdout


def upload(image: Path, region: str, tags: list[str], description: str) -> str:
    data = image.read_bytes()
    blocks = list(changed_blocks(data))
    tag_args = []
    for t in tags:
        k, _, v = t.partition("=")
        tag_args.append(f"Key={k},Value={v}")
    start = json.loads(_aws(
        region, "ebs", "start-snapshot",
        "--volume-size", str(volume_gib(len(data))),
        "--timeout", "60",
        "--description", description,
        *(["--tags", *tag_args] if tag_args else []),
    ))
    snap = start["SnapshotId"]
    # The id goes to stderr at once, so a caller's cleanup can delete it even
    # if a block upload below fails.
    print(f"snapshot started: {snap}", file=sys.stderr, flush=True)

    with tempfile.TemporaryDirectory() as tmp:
        def put(block: tuple[int, bytes, str]) -> None:
            idx, chunk, digest = block
            path = Path(tmp) / f"{idx}.blk"
            path.write_bytes(chunk)
            _aws(region, "ebs", "put-snapshot-block",
                 "--snapshot-id", snap, "--block-index", str(idx),
                 # A streaming blob: the CLI takes a bare path here and
                 # rejects fileb:// ("Blob values must be a path to a file").
                 "--block-data", str(path), "--data-length", str(BLOCK),
                 "--checksum", digest, "--checksum-algorithm", "SHA256")
            path.unlink()

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(put, blocks))

    _aws(region, "ebs", "complete-snapshot", "--snapshot-id", snap,
         "--changed-blocks-count", str(len(blocks)))
    _aws(region, "ec2", "wait", "snapshot-completed", "--snapshot-ids", snap)
    print(f"snapshot completed: {snap} ({len(blocks)} blocks)", file=sys.stderr)
    return snap


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("upload")
    up.add_argument("image", type=Path)
    up.add_argument("--region", required=True)
    up.add_argument("--tag", action="append", default=[])
    up.add_argument("--description", default="harland boot-run image (AGAST #1849)")
    pl = sub.add_parser("plan")
    pl.add_argument("image", type=Path)
    args = ap.parse_args(argv)

    if args.cmd == "plan":
        data = args.image.read_bytes()
        n = sum(1 for _ in changed_blocks(data))
        print(f"{args.image}: {len(data)} bytes, {n} non-zero blocks, "
              f"{volume_gib(len(data))} GiB volume")
        return 0
    print(upload(args.image, args.region, args.tag, args.description))
    return 0


if __name__ == "__main__":
    sys.exit(main())
