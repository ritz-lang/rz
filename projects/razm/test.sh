#!/bin/bash
# razm against the oracle (`as --64`, `ld.lld`), one test per corpus file and
# synthetic fixture; every one must assemble and match.
set -u
cd "$(dirname "$0")"
# The bin link build_package makes here, or in test_run_dir's shadow.
[ -x razm ] && export RAZM="$PWD/razm"
exec python3 -m pytest -q -p no:cacheprovider tests
