"""tools/ runs under ritz0's spawn_guard (AGAST #4092).

AGAST #1805's rule (a test that starts a process must be `integration`) is
enforced by ritz0/harness/spawn_guard.py, which ritz0/conftest.py loads.  `make
tools-unit` runs `pytest tools/`, which never reads ritz0/conftest.py, so for
tools/ the rule was on the honour system: on 2026-11-18, 454 unmarked tools/
tests started a process.  tools/conftest.py now loads the guard too.  These
checks are pure: they inspect this session, and start nothing.
"""

import os
import subprocess

import pytest

pytestmark = pytest.mark.unit


def test_this_session_loads_spawn_guard(request):
    assert request.config.pluginmanager.has_plugin("spawn_guard"), (
        "tools/ ran without ritz0/harness/spawn_guard.py: tools/conftest.py must load it")


def test_the_guard_is_armed(request):
    # Loaded but not configured would leave Popen and os.system untouched.
    spawn_guard = request.config.pluginmanager.get_plugin("spawn_guard")
    assert subprocess.Popen.__init__ is spawn_guard._popen_init
    assert os.system is spawn_guard._system
