#!/usr/bin/env python3
"""Turn one builder run's logs and build tree into /out (AGAST #4823).

`parse-test` reads an `rz test` log and prints the count record the
acceptance script compares. `finish` writes summary.json, copies binaries
and object files into the output directory, and exits 0 only when the
build succeeded and, unless this was build-only, every test passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

_OK = re.compile(r"Σ ✓ (\d+) of (\d+) files passed \((\d+) tests\)")
_BAD = re.compile(
    r"Σ ✗ (\d+) of (\d+) files FAILED: (.*) \| (\d+) file\(s\) passed, (\d+) tests passed"
)
_FAILED_N = re.compile(r"\((\d+) failed\)")


def parse_test(text: str, rc: int) -> dict:
    """Counts from the last Σ line, or zeros when the package has no tests.

    A log with neither a Σ line nor a recognized no-test note is
    `unparsed`: the entrypoint treats that as a failure so a changed rz
    summary cannot look like a green run with missing numbers.
    """
    ok = list(_OK.finditer(text))
    bad = list(_BAD.finditer(text))
    record: dict
    if ok or bad:
        # The later of the two kinds. One package prints one Σ line.
        if ok and (not bad or ok[-1].start() > bad[-1].start()):
            m = ok[-1]
            record = {
                "exit": rc,
                "files": int(m.group(2)),
                "files_passed": int(m.group(1)),
                "passed": int(m.group(3)),
                "failed": 0,
            }
        else:
            m = bad[-1]
            failed = 0
            fm = _FAILED_N.search(m.group(3))
            if fm:
                failed = int(fm.group(1))
            record = {
                "exit": rc,
                "files": int(m.group(2)),
                "files_passed": int(m.group(4)),
                "passed": int(m.group(5)),
                "failed": failed,
            }
    elif "No tests found, skipping" in text:
        record = {"exit": rc, "files": 0, "files_passed": 0, "passed": 0, "failed": 0}
    elif "✓ test.sh passed" in text or "✗ test.sh failed" in text:
        record = {"exit": rc, "files": 0, "files_passed": 0, "passed": 0, "failed": 0}
    else:
        record = {"exit": rc, "unparsed": True}
    if "✓ test.sh passed" in text:
        record["test_sh"] = "pass"
    elif "✗ test.sh failed" in text or "test.sh failed:" in text:
        record["test_sh"] = "fail"
    return record


def _elf_or_pe(path: Path) -> bool:
    try:
        magic = path.read_bytes()[:4]
    except OSError:
        return False
    return magic == b"\x7fELF" or magic[:2] == b"MZ"


def copy_bins(package_build: Path, out: Path) -> list[str]:
    """ELF and PE files from the package build tree, by basename."""
    dest_dir = out / "bin"
    dest_dir.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    if not package_build.is_dir():
        return names
    skip_suffix = {".o", ".ll", ".bc", ".json", ".d", ".s", ".a"}
    for path in sorted(package_build.rglob("*")):
        if not path.is_file() or path.suffix in skip_suffix:
            continue
        if path.name.endswith(".manifest.json"):
            continue
        if not _elf_or_pe(path):
            continue
        shutil.copy2(path, dest_dir / path.name)
        names.append(path.name)
    return names


def copy_objects(cas_root: Path, out: Path) -> int:
    """Object files from this run's content-addressed store.

    Named from the store's module identity when it has one, so a freestanding
    build (whose scratch directory rz deletes) still leaves `.o` files in
    /out. Two modules with the same file name get a short key prefix.
    """
    dest_dir = out / "obj"
    dest_dir.mkdir(parents=True, exist_ok=True)
    objects = cas_root / "objects"
    if not objects.is_dir():
        return 0
    n = 0
    for obj in sorted(objects.rglob("*.o")):
        key = obj.name[:-2]
        name = key[:12] + ".o"
        meta_path = cas_root / "meta" / key[:2] / f"{key}.json"
        if meta_path.is_file():
            try:
                module = json.loads(meta_path.read_text()).get("module") or ""
            except (OSError, json.JSONDecodeError):
                module = ""
            if module:
                flat = module.replace("/", "_")
                if flat.endswith(".ritz"):
                    flat = flat[: -len(".ritz")]
                name = flat + ".o"
        dest = dest_dir / name
        if dest.exists():
            dest = dest_dir / f"{key[:8]}_{name}"
        shutil.copy2(obj, dest)
        n += 1
    return n


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def finish(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    build_rc = int(args.build_rc)
    test_rc = int(args.test_rc)
    build_only = args.build_only == "1"
    if build_rc != 0:
        test = {"skipped": True, "reason": "build failed"}
    elif build_only:
        test = {"skipped": True, "reason": "build-only"}
    else:
        test = parse_test(Path(args.test_log).read_text(errors="replace"), test_rc)

    package_build = Path(args.package_build)
    build_copy = out / "build"
    if build_copy.exists():
        shutil.rmtree(build_copy)
    if package_build.is_dir():
        shutil.copytree(package_build, build_copy, symlinks=True)
    bins = copy_bins(package_build, out)
    objects = copy_objects(Path(args.cas), out)

    name = ""
    manifest = Path(args.manifest)
    if manifest.is_file():
        import tomllib
        name = tomllib.loads(manifest.read_text()).get("package", {}).get("name", "")

    ok = build_rc == 0 and not test.get("unparsed") and (build_only or test_rc == 0)
    summary = {
        "package": name,
        "source": args.source,
        "compiler": "ritz1_selfhosted",
        "ritz1": args.ritz1,
        "ritz1_sha256": _sha256(Path(args.ritz1)) if Path(args.ritz1).is_file() else "",
        "build_only": build_only,
        "build": {"exit": build_rc},
        "test": test,
        "bins": bins,
        "objects": objects,
        "ok": ok,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    parse = sub.add_parser("parse-test")
    parse.add_argument("log")
    parse.add_argument("rc")

    fin = sub.add_parser("finish")
    fin.add_argument("--out", required=True)
    fin.add_argument("--build-log", required=True)
    fin.add_argument("--build-rc", required=True)
    fin.add_argument("--test-log", required=True)
    fin.add_argument("--test-rc", required=True)
    fin.add_argument("--build-only", required=True, choices=("0", "1"))
    fin.add_argument("--package-build", required=True)
    fin.add_argument("--cas", required=True)
    fin.add_argument("--source", required=True)
    fin.add_argument("--manifest", required=True)
    fin.add_argument("--ritz1", required=True)

    args = parser.parse_args(argv)
    if args.cmd == "parse-test":
        text = Path(args.log).read_text(errors="replace") if args.log != "-" else sys.stdin.read()
        json.dump(parse_test(text, int(args.rc)), sys.stdout)
        sys.stdout.write("\n")
        return 0
    return finish(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
