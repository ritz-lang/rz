#!/bin/bash
# razm against the oracle (`as --64`, `ld.lld`), one test per corpus file.
# A file razm does not assemble yet is an expected failure naming that file
# (-rx prints each); it never passes or skips silently.
set -u
cd "$(dirname "$0")"
# The bin link build_package makes here, or in test_run_dir's shadow.
[ -x razm ] && export RAZM="$PWD/razm"
exec python3 -m pytest -q -rxX -p no:cacheprovider tests
