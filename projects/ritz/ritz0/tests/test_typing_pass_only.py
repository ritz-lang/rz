"""Test helper: the source typing pass's verdict through ritz0's passes (AGAST #4260).

ritz0 reports the typing pass's errors after _emit, so where the emitter
refuses a program too, its words are the ones printed.  A test of the
typing pass's own rules (its wording, where it points) runs the compile
without _monomorph, _check_instances (which re-types each instance, and
would report first), _emit and _write: _check_types then judges the source
module, as it would if the emitter had accepted the program.
"""

import contextlib
import io
import os
from types import SimpleNamespace

import ritz0

SKIPPED = (ritz0._monomorph, ritz0._check_instances, ritz0._emit, ritz0._write)


@contextlib.contextmanager
def _env(ritz_path):
    old = os.environ.get("RITZ_PATH")
    if ritz_path is not None:
        os.environ["RITZ_PATH"] = str(ritz_path)
    try:
        yield
    finally:
        if ritz_path is None:
            pass
        elif old is None:
            os.environ.pop("RITZ_PATH", None)
        else:
            os.environ["RITZ_PATH"] = old


def compile_typing_only(source_path, output_path, ritz_path=None, **kwargs):
    """ritz0.compile_file(source_path, output_path, **kwargs) without the
    SKIPPED passes, in-process.  Returns (returncode, stdout, stderr) like a
    CompletedProcess: 0 if every pass accepted the program."""
    out, err = io.StringIO(), io.StringIO()
    passes = ritz0.PASSES
    ritz0.PASSES = tuple(p for p in passes if p not in SKIPPED)
    try:
        with _env(ritz_path), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            ok = ritz0.compile_file(str(source_path), str(output_path), **kwargs)
    finally:
        ritz0.PASSES = passes
    return SimpleNamespace(returncode=0 if ok else 1, stdout=out.getvalue(),
                           stderr=err.getvalue())
