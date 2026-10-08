#!/usr/bin/env python3
"""ritz0's "Skipped X (unchanged)" fast path must account for imports (AGAST #1674).

Background
----------
``compile_file`` skips all work when the ``.ll`` is newer than the source and
the source hash matches ``source_hash`` in ``<src>.ritz.sig``. That checked the
module's OWN source only. But a module's ``.ll`` also depends on every
transitive import: struct layouts (field offsets, GEP indices), constants,
and declared signatures are all baked in from imported sources.

So when an imported struct gained a field, make (correctly, via the #1659
``.d`` deps) re-ran ritz0 on each importer, and ritz0 replied "Skipped" and
kept the stale ``.ll``. In ritz1 that meant ``emitter_expr_arith.ll`` read
``s.current_label`` from the old offset and emitted ``phi i64 [ 0, %L32766 ]``
for every short-circuit ``and``.

The fix records a hash of every transitive import in the sig
(``import_hashes``) and the fast path requires all of them to still match.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RITZ0_DIR))

from emitter.fn_cache import (  # noqa: E402
    build_sig_data,
    check_import_hashes,
    source_file_hash,
)


def _compile(main: Path, out: Path) -> subprocess.CompletedProcess:
    """Run ritz0 on ``main`` as make would: a fresh process per invocation."""
    result = subprocess.run(
        [sys.executable, str(RITZ0_DIR / "ritz0.py"), str(main), "-o", str(out)],
        capture_output=True, text=True, cwd=str(main.parent),
    )
    assert result.returncode == 0, f"compile failed:\n{result.stdout}\n{result.stderr}"
    return result


@pytest.fixture
def three_level(tmp_path):
    """main imports mid, mid imports base. base owns the struct layout."""
    base = tmp_path / "base.ritz"
    base.write_text(
        "pub struct Rec\n"
        "    a: i64\n"
        "    b: i64\n"
    )
    mid = tmp_path / "mid.ritz"
    mid.write_text(
        "import base\n\n"
        "pub fn mid_id(x: i64) -> i64\n"
        "    x\n"
    )
    main = tmp_path / "main.ritz"
    main.write_text(
        "import mid\n"
        "import base\n\n"
        "fn get_b(r: *Rec) -> i64\n"
        "    r.b\n\n"
        "fn main() -> i32\n"
        "    0\n"
    )
    return tmp_path, base, mid, main


@pytest.mark.integration
class TestFastPathHonoursImports:
    def test_unchanged_tree_still_skips(self, three_level):
        """Control: the fast path must keep working when nothing changed."""
        tmp, _base, _mid, main = three_level
        out = tmp / "main.ll"
        _compile(main, out)
        second = _compile(main, out)
        assert "Skipped" in second.stdout, second.stdout

    def test_changed_import_struct_layout_recompiles(self, three_level):
        """Inserting a field before `b` in an imported struct must re-emit main.ll."""
        tmp, base, _mid, main = three_level
        out = tmp / "main.ll"
        _compile(main, out)
        old_ir = out.read_text()

        # Shift `b` from field 1 to field 2, as #1671 did to LocalVar.
        base.write_text(
            "pub struct Rec\n"
            "    a: i64\n"
            "    pad: i64\n"
            "    b: i64\n"
        )
        second = _compile(main, out)
        assert "Skipped" not in second.stdout, (
            "ritz0 skipped main.ritz although its import base.ritz changed: "
            + second.stdout
        )
        assert out.read_text() != old_ir, "main.ll kept the stale layout"

    def test_changed_transitive_import_recompiles(self, three_level):
        """A change two imports deep (main -> mid -> base) also invalidates."""
        tmp, base, mid, main = three_level
        # main stops importing base directly; it now only reaches it via mid.
        main.write_text(
            "import mid\n\n"
            "fn main() -> i32\n"
            "    0\n"
        )
        out = tmp / "main.ll"
        _compile(main, out)
        base.write_text(base.read_text() + "    c: i64\n")
        second = _compile(main, out)
        assert "Skipped" not in second.stdout, second.stdout

    def test_sig_without_import_hashes_recompiles(self, three_level):
        """A sig written before #1674 carries no import record; never trust it."""
        tmp, _base, _mid, main = three_level
        out = tmp / "main.ll"
        _compile(main, out)
        sig_path = tmp / "main.ritz.sig"
        data = json.loads(sig_path.read_text())
        data.pop("import_hashes", None)
        sig_path.write_text(json.dumps(data))
        out.touch()  # keep the .ll newer than the source
        second = _compile(main, out)
        assert "Skipped" not in second.stdout, second.stdout


@pytest.mark.unit
class TestCheckImportHashes:
    def test_missing_key_is_stale(self):
        assert check_import_hashes({"source_hash": "x", "functions": {}}) is False

    def test_none_sig_is_stale(self):
        assert check_import_hashes(None) is False

    def test_no_imports_is_fresh(self):
        assert check_import_hashes({"import_hashes": {}}) is True

    def test_matching_hashes_are_fresh(self, tmp_path):
        f = tmp_path / "lib.ritz"
        f.write_text("pub fn f() -> i32\n    1\n")
        sig = {"import_hashes": {str(f): source_file_hash(f.read_text())}}
        assert check_import_hashes(sig) is True

    def test_changed_import_is_stale(self, tmp_path):
        f = tmp_path / "lib.ritz"
        f.write_text("pub fn f() -> i32\n    1\n")
        sig = {"import_hashes": {str(f): source_file_hash(f.read_text())}}
        f.write_text("pub fn f() -> i32\n    2\n")
        assert check_import_hashes(sig) is False

    def test_deleted_import_is_stale(self, tmp_path):
        f = tmp_path / "gone.ritz"
        sig = {"import_hashes": {str(f): "deadbeef"}}
        assert check_import_hashes(sig) is False

    def test_build_sig_data_records_import_hashes(self):
        data = build_sig_data(
            source="fn main() -> i32\n    0\n",
            fn_hashes={},
            import_hashes={"/x/lib.ritz": "abc"},
        )
        assert data["import_hashes"] == {"/x/lib.ritz": "abc"}
