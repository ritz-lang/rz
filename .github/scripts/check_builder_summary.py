#!/usr/bin/env python3
"""Judge one builder run's summary.json (AGAST #4825, #4826, #4846).

    check_builder_summary.py <summary.json> <package> <build-only: 0|1>

Shared by the two places a package runs through the builder image:
run_builder_package.sh (GitHub's builder-matrix, `docker run`) and
woodpecker_builder_step.sh (huburght's Woodpecker, the step pod IS the
image). Both runs exit 0 only when the build succeeded and every test
passed (projects/builder/README.md); this adds the one check the image can't
make for itself: a package whose summary reports zero tests passed is a
silently-empty run, not a green one (summary.py's "No tests found, skipping"
parses to passed=0, ok=true). A passing test.sh is a suite that ran,
counted or not (rllvm's is pytest). A package with no tests at all is run
build-only, which the matrix decides from the package's files.

Exit: 0 built (and, unless build-only, tested, at least one test passed);
1 not ok, or zero tests passed; 2 bad arguments.
"""

from __future__ import annotations

import json
import sys


def main(argv: list[str]) -> int:
    if len(argv) != 4 or argv[3] not in ("0", "1"):
        print("usage: check_builder_summary.py <summary.json> <package> <0|1>",
              file=sys.stderr)
        return 2
    summary_path, pkg, build_only = argv[1], argv[2], argv[3] == "1"
    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)
    if not summary.get("ok"):
        print(f"run_builder_package: {pkg}: run not ok: {json.dumps(summary)}",
              file=sys.stderr)
        return 1
    if build_only:
        print(f"run_builder_package: {pkg}: built (build only): the package has no tests")
        return 0
    test = summary.get("test", {})
    passed = test.get("passed", 0)
    if passed <= 0 and test.get("test_sh") == "pass":
        # A test.sh-only suite (rllvm's pytest): summary.py counts ritzunit
        # tests, and records the script's verdict apart.
        print(f"run_builder_package: {pkg}: test.sh passed (no ritzunit tests)")
        return 0
    if passed <= 0:
        print(f"run_builder_package: {pkg}: ran zero tests: {json.dumps(summary)}",
              file=sys.stderr)
        return 1
    print(f"run_builder_package: {pkg}: {passed} test(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
