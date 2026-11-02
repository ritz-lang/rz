#!/usr/bin/env python3
"""ritz0's "Skipped X (unchanged)" fast path must account for imports (AGAST #1674).

Background
----------
``compile_file`` skips all work when the ``.ll`` is newer than the source and
the source hash matches ``source_hash`` in the source's sig file. That checked the
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
import os
import subprocess
import sys
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RITZ0_DIR))

from emitter.fn_cache import (  # noqa: E402
    build_sig_data,
    check_import_hashes,
    check_import_misses,
    sig_path_for,
    source_file_hash,
)
from ritz0_inproc import run_ritz0  # noqa: E402


def _compile(main: Path, out: Path) -> subprocess.CompletedProcess:
    """Run ritz0 on ``main`` as make would: a fresh process (fork) per invocation."""
    result = run_ritz0([str(main), "-o", str(out)], cwd=str(main.parent))
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
        sig_path = sig_path_for(main)
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


# ---------------------------------------------------------------------------
# A new file that shadows a resolved import (AGAST #2030)
# ---------------------------------------------------------------------------
#
# `import_hashes` vouches only for the files the last compile READ.  Import
# resolution is first match (importer's dir as foo/bar.ritz then foo.bar.ritz,
# source roots, project root, RITZ_PATH), so a NEW file at a candidate probed
# before the hit changes what the import resolves to while every recorded
# hash still matches.  The sig records those probed-and-missed candidates
# (`import_misses`) and the fast path requires them to still be missing.

TAG_SRC = "pub const LIB_TAG: i32 = {}\n"
TAG_MAIN = "import shared.tag\n\nfn main() -> i32\n    LIB_TAG\n"


def _tag_tree(tmp_path: Path):
    """app/main.ritz imports shared.tag, which only rootB provides (202)."""
    app = tmp_path / "app"
    app.mkdir()
    main = app / "main.ritz"
    main.write_text(TAG_MAIN)
    root_b = tmp_path / "rootB"
    (root_b / "shared").mkdir(parents=True)
    (root_b / "shared" / "tag.ritz").write_text(TAG_SRC.format(202))
    return main, root_b


def _place(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TAG_SRC.format(value))


def _compile_env(main: Path, out: Path, ritz_path: str, cache: Path):
    env = dict(os.environ, RITZ_PATH=ritz_path, RITZ_CACHE_DIR=str(cache))
    result = run_ritz0([str(main), "-o", str(out)], cwd=str(main.parent), env=env)
    assert result.returncode == 0, f"compile failed:\n{result.stdout}\n{result.stderr}"
    return result


def _assert_shadow_recompiles(tmp_path, main, out, ritz_path, shadow):
    cache = tmp_path / "cache"
    _compile_env(main, out, ritz_path, cache)
    assert "202" in out.read_text()
    _place(shadow, 101)
    second = _compile_env(main, out, ritz_path, cache)
    assert "Skipped" not in second.stdout, (
        "fast path kept IR for the import's OLD resolution: " + second.stdout)
    cold = tmp_path / "cold.ll"
    _compile_env(main, cold, ritz_path, tmp_path / "cold-cache")
    assert "101" in cold.read_text(), "test is vacuous: cold IR lacks the new tag"
    assert out.read_text() == cold.read_text()


@pytest.mark.integration
class TestFastPathSeesShadowingImports:
    def test_ticket_repro_new_file_in_source_dir(self, tmp_path):
        main, root_b = _tag_tree(tmp_path)
        _assert_shadow_recompiles(tmp_path, main, main.parent / "a.ll", str(root_b),
                                  main.parent / "shared" / "tag.ritz")

    def test_new_flat_named_file_in_source_dir(self, tmp_path):
        """The importer's dir is also probed for `shared.tag.ritz`."""
        main, root_b = _tag_tree(tmp_path)
        _assert_shadow_recompiles(tmp_path, main, main.parent / "a.ll", str(root_b),
                                  main.parent / "shared.tag.ritz")

    def test_new_file_in_earlier_ritz_path_entry(self, tmp_path):
        main, root_b = _tag_tree(tmp_path)
        root_a = tmp_path / "rootA"
        root_a.mkdir()
        _assert_shadow_recompiles(tmp_path, main, main.parent / "a.ll",
                                  f"{root_a}:{root_b}", root_a / "shared" / "tag.ritz")

    def test_earlier_ritz_path_entry_created_later(self, tmp_path):
        """An entry that did not exist at the first compile is still a candidate."""
        main, root_b = _tag_tree(tmp_path)
        root_a = tmp_path / "rootA"
        _assert_shadow_recompiles(tmp_path, main, main.parent / "a.ll",
                                  f"{root_a}:{root_b}", root_a / "shared" / "tag.ritz")

    def test_new_file_after_the_hit_keeps_the_fast_path(self, tmp_path):
        """Guard: only candidates probed BEFORE the hit can shadow it."""
        main, root_b = _tag_tree(tmp_path)
        root_c = tmp_path / "rootC"
        root_c.mkdir()
        out = main.parent / "a.ll"
        cache = tmp_path / "cache"
        _compile_env(main, out, f"{root_b}:{root_c}", cache)
        _place(root_c / "shared" / "tag.ritz", 101)
        _place(root_b / "shared.tag.ritz", 101)
        second = _compile_env(main, out, f"{root_b}:{root_c}", cache)
        assert "Skipped" in second.stdout, second.stdout

    def test_sig_without_import_misses_recompiles(self, tmp_path):
        """A sig written before #2030 cannot vouch for its missed candidates."""
        main, root_b = _tag_tree(tmp_path)
        out = main.parent / "a.ll"
        cache = tmp_path / "cache"
        _compile_env(main, out, str(root_b), cache)
        sig = cache / "ritz0" / (os.path.realpath(main).lstrip("/") + ".sig")
        data = json.loads(sig.read_text())
        assert str(main.parent / "shared" / "tag.ritz") in data["import_misses"]
        data.pop("import_misses")
        sig.write_text(json.dumps(data))
        out.touch()
        second = _compile_env(main, out, str(root_b), cache)
        assert "Skipped" not in second.stdout, second.stdout


@pytest.mark.unit
class TestCheckImportMisses:
    def test_missing_key_is_stale(self):
        assert check_import_misses({"import_hashes": {}}) is False

    def test_none_sig_is_stale(self):
        assert check_import_misses(None) is False

    def test_no_misses_is_fresh(self):
        assert check_import_misses({"import_misses": []}) is True

    def test_still_missing_is_fresh(self, tmp_path):
        assert check_import_misses({"import_misses": [str(tmp_path / "no.ritz")]}) is True

    def test_now_existing_is_stale(self, tmp_path):
        f = tmp_path / "now.ritz"
        f.write_text("")
        assert check_import_misses({"import_misses": [str(f)]}) is False

    def test_malformed_record_is_stale(self):
        assert check_import_misses({"import_misses": {"a": 1}}) is False
        assert check_import_misses({"import_misses": [3]}) is False

    def test_build_sig_data_records_import_misses(self):
        data = build_sig_data(source="fn main() -> i32\n    0\n", fn_hashes={},
                              import_misses=["/x/b.ritz", "/x/a.ritz"])
        assert data["import_misses"] == ["/x/a.ritz", "/x/b.ritz"]
