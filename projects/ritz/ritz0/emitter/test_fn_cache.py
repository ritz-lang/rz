"""
Tests for per-function incremental compilation cache (emitter/fn_cache.py).

Tests cover:
  - Token hashing (whitespace invariance, determinism)
  - Source file hashing
  - Hash map building
  - .ritz.sig file I/O (read, write, corrupt handling)
  - Cache hit/miss detection
  - Signature change detection
  - Dependent invalidation
  - Cached IR retrieval
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure ritz0 dir is in path
ritz0_dir = str(Path(__file__).parent.parent)
if ritz0_dir not in sys.path:
    sys.path.insert(0, ritz0_dir)

from emitter.fn_cache import (
    fn_token_hash,
    sig_token_hash,
    source_file_hash,
    build_hash_map,
    build_sig_hash_map,
    read_sig_file,
    write_sig_file,
    delete_sig_file,
    check_cache,
    get_cached_ir,
    check_source_hash,
    build_sig_data,
    detect_sig_changes,
    invalidate_dependents,
    _sig_path,
    _path_to_import_name,
)
from lexer import Lexer
from tokens import TokenType, Token, Span


# ============================================================================
# Token Hashing Tests
# ============================================================================

class TestFnTokenHash:
    """Tests for fn_token_hash()."""

    def _lex(self, source: str) -> list:
        """Helper to lex source code into tokens."""
        lexer = Lexer(source, "<test>")
        return lexer.tokenize()

    @pytest.mark.unit
    def test_deterministic(self):
        """Same token stream always produces same hash."""
        tokens = self._lex("fn foo() -> i32\n    42\n")
        h1 = fn_token_hash(tokens)
        tokens2 = self._lex("fn foo() -> i32\n    42\n")
        h2 = fn_token_hash(tokens2)
        assert h1 == h2
        assert len(h1) == 16  # 16 hex chars

    @pytest.mark.unit
    def test_whitespace_invariant(self):
        """Different whitespace/indentation produces same hash."""
        src1 = "fn foo() -> i32\n    42\n"
        src2 = "fn foo() -> i32\n        42\n"
        h1 = fn_token_hash(self._lex(src1))
        h2 = fn_token_hash(self._lex(src2))
        assert h1 == h2

    @pytest.mark.unit
    def test_different_body_different_hash(self):
        """Different function bodies produce different hashes."""
        h1 = fn_token_hash(self._lex("fn foo() -> i32\n    42\n"))
        h2 = fn_token_hash(self._lex("fn foo() -> i32\n    99\n"))
        assert h1 != h2

    @pytest.mark.unit
    def test_empty_tokens(self):
        """Empty token list produces a hash (not an error)."""
        h = fn_token_hash([])
        assert len(h) == 16

    @pytest.mark.unit
    def test_sig_hash_different_from_body_hash(self):
        """Signature hash and body hash are different."""
        tokens = self._lex("fn foo(x: i32) -> i32\n    x + 1\n")
        body_hash = fn_token_hash(tokens)
        sig_hash = sig_token_hash(tokens)
        # They should be different because body_hash includes the body
        assert body_hash != sig_hash


# ============================================================================
# Source File Hash Tests
# ============================================================================

class TestSourceFileHash:
    """Tests for source_file_hash()."""

    @pytest.mark.unit
    def test_deterministic(self):
        """Same source always produces same hash."""
        src = "fn main() -> i32\n    0\n"
        assert source_file_hash(src) == source_file_hash(src)

    @pytest.mark.unit
    def test_different_source_different_hash(self):
        """Different source produces different hash."""
        h1 = source_file_hash("fn foo() -> i32\n    1\n")
        h2 = source_file_hash("fn foo() -> i32\n    2\n")
        assert h1 != h2

    @pytest.mark.unit
    def test_length(self):
        """Hash is 16 hex characters."""
        h = source_file_hash("hello")
        assert len(h) == 16


# ============================================================================
# Hash Map Building Tests
# ============================================================================

class TestBuildHashMap:
    """Tests for build_hash_map()."""

    @pytest.mark.unit
    def test_single_function(self):
        """Hash map contains one entry for a single function."""
        src = "fn foo() -> i32\n    42\n"
        hm = build_hash_map(src)
        assert 'foo' in hm
        assert len(hm) == 1
        assert len(hm['foo']) == 16

    @pytest.mark.unit
    def test_multiple_functions(self):
        """Hash map contains entries for all functions."""
        src = "fn foo() -> i32\n    1\n\nfn bar() -> i32\n    2\n"
        hm = build_hash_map(src)
        assert 'foo' in hm
        assert 'bar' in hm
        assert hm['foo'] != hm['bar']

    @pytest.mark.unit
    def test_ignores_non_functions(self):
        """Hash map only contains functions, not structs/enums/etc."""
        src = "struct Foo\n    x: i32\n\nfn bar() -> i32\n    1\n"
        hm = build_hash_map(src)
        assert 'Foo' not in hm
        assert 'bar' in hm

    @pytest.mark.unit
    def test_sig_hash_map_pub_only(self):
        """Signature hash map only includes pub functions."""
        src = "pub fn foo() -> i32\n    1\n\nfn bar() -> i32\n    2\n"
        shm = build_sig_hash_map(src)
        assert 'foo' in shm
        assert 'bar' not in shm


# ============================================================================
# Sig File I/O Tests
# ============================================================================

class TestSigFileIO:
    """Tests for read/write/delete sig file operations."""

    @pytest.mark.unit
    def test_read_missing_file(self):
        """Reading a non-existent sig file returns None."""
        result = read_sig_file("/nonexistent/path/file.ritz")
        assert result is None

    @pytest.mark.unit
    def test_write_and_read(self):
        """Write and read back a sig file."""
        with tempfile.NamedTemporaryFile(suffix='.ritz', delete=False) as f:
            source_path = f.name

        try:
            data = {
                'source_hash': 'abc123',
                'functions': {
                    'foo': {'hash': 'def456', 'ir': 'define i32 @foo() { ret i32 42 }'}
                },
                'imports': [],
            }
            write_sig_file(source_path, data)
            result = read_sig_file(source_path)
            assert result is not None
            assert result['source_hash'] == 'abc123'
            assert result['functions']['foo']['hash'] == 'def456'
        finally:
            Path(source_path).unlink(missing_ok=True)
            _sig_path(source_path).unlink(missing_ok=True)

    @pytest.mark.unit
    def test_read_corrupt_json(self):
        """Reading a corrupt sig file returns None."""
        with tempfile.NamedTemporaryFile(suffix='.ritz', delete=False) as f:
            source_path = f.name

        try:
            sig_file = _sig_path(source_path)
            sig_file.write_text("not valid json {{{")
            result = read_sig_file(source_path)
            assert result is None
        finally:
            Path(source_path).unlink(missing_ok=True)
            sig_file.unlink(missing_ok=True)

    @pytest.mark.unit
    def test_read_invalid_structure(self):
        """Reading a sig file without 'functions' key returns None."""
        with tempfile.NamedTemporaryFile(suffix='.ritz', delete=False) as f:
            source_path = f.name

        try:
            sig_file = _sig_path(source_path)
            sig_file.write_text(json.dumps({"not_functions": {}}))
            result = read_sig_file(source_path)
            assert result is None
        finally:
            Path(source_path).unlink(missing_ok=True)
            sig_file.unlink(missing_ok=True)

    @pytest.mark.unit
    def test_delete_sig_file(self):
        """Delete a sig file."""
        with tempfile.NamedTemporaryFile(suffix='.ritz', delete=False) as f:
            source_path = f.name

        try:
            data = {'source_hash': 'x', 'functions': {}, 'imports': []}
            write_sig_file(source_path, data)
            assert _sig_path(source_path).exists()
            delete_sig_file(source_path)
            assert not _sig_path(source_path).exists()
        finally:
            Path(source_path).unlink(missing_ok=True)
            _sig_path(source_path).unlink(missing_ok=True)

    @pytest.mark.unit
    def test_delete_nonexistent_is_noop(self):
        """Deleting a nonexistent sig file doesn't raise."""
        delete_sig_file("/nonexistent/path/file.ritz")


# ============================================================================
# Cache Detection Tests
# ============================================================================

class TestCheckCache:
    """Tests for check_cache()."""

    @pytest.mark.unit
    def test_no_cache_all_misses(self):
        """With no cache data, everything is a miss."""
        current = {'foo': 'abc', 'bar': 'def'}
        hits, misses = check_cache(current, None)
        assert hits == {}
        assert misses == current

    @pytest.mark.unit
    def test_all_hits(self):
        """When all hashes match, everything is a hit."""
        current = {'foo': 'abc', 'bar': 'def'}
        sig_data = {
            'functions': {
                'foo': {'hash': 'abc'},
                'bar': {'hash': 'def'},
            }
        }
        hits, misses = check_cache(current, sig_data)
        assert hits == current
        assert misses == {}

    @pytest.mark.unit
    def test_mixed_hits_and_misses(self):
        """Some functions match, some don't."""
        current = {'foo': 'abc', 'bar': 'changed'}
        sig_data = {
            'functions': {
                'foo': {'hash': 'abc'},
                'bar': {'hash': 'original'},
            }
        }
        hits, misses = check_cache(current, sig_data)
        assert hits == {'foo': 'abc'}
        assert misses == {'bar': 'changed'}

    @pytest.mark.unit
    def test_new_function_is_miss(self):
        """A function not in the cache is a miss."""
        current = {'foo': 'abc', 'new_fn': 'xyz'}
        sig_data = {
            'functions': {
                'foo': {'hash': 'abc'},
            }
        }
        hits, misses = check_cache(current, sig_data)
        assert hits == {'foo': 'abc'}
        assert misses == {'new_fn': 'xyz'}


# ============================================================================
# Cached IR Tests
# ============================================================================

class TestGetCachedIR:
    """Tests for get_cached_ir()."""

    @pytest.mark.unit
    def test_get_existing_ir(self):
        """Can retrieve cached IR for a function."""
        sig_data = {
            'functions': {
                'foo': {'hash': 'abc', 'ir': 'define i32 @foo() { ret i32 42 }'},
            }
        }
        ir = get_cached_ir('foo', sig_data)
        assert ir == 'define i32 @foo() { ret i32 42 }'

    @pytest.mark.unit
    def test_no_ir_returns_none(self):
        """Returns None when no IR cached."""
        sig_data = {
            'functions': {
                'foo': {'hash': 'abc', 'ir': ''},
            }
        }
        assert get_cached_ir('foo', sig_data) is None

    @pytest.mark.unit
    def test_missing_function_returns_none(self):
        """Returns None for unknown function."""
        sig_data = {'functions': {}}
        assert get_cached_ir('nonexistent', sig_data) is None


# ============================================================================
# Source Hash Check Tests
# ============================================================================

class TestCheckSourceHash:
    """Tests for check_source_hash()."""

    @pytest.mark.unit
    def test_matching_hash(self):
        """Returns True when source hash matches cached hash."""
        src = "fn foo() -> i32\n    42\n"
        with tempfile.NamedTemporaryFile(suffix='.ritz', delete=False) as f:
            source_path = f.name

        try:
            data = {
                'source_hash': source_file_hash(src),
                'functions': {},
                'imports': [],
            }
            write_sig_file(source_path, data)
            assert check_source_hash(src, source_path) is True
        finally:
            Path(source_path).unlink(missing_ok=True)
            _sig_path(source_path).unlink(missing_ok=True)

    @pytest.mark.unit
    def test_mismatched_hash(self):
        """Returns False when source hash doesn't match."""
        with tempfile.NamedTemporaryFile(suffix='.ritz', delete=False) as f:
            source_path = f.name

        try:
            data = {
                'source_hash': 'old_hash_value',
                'functions': {},
                'imports': [],
            }
            write_sig_file(source_path, data)
            assert check_source_hash("new source code", source_path) is False
        finally:
            Path(source_path).unlink(missing_ok=True)
            _sig_path(source_path).unlink(missing_ok=True)

    @pytest.mark.unit
    def test_no_sig_file(self):
        """Returns False when no sig file exists."""
        assert check_source_hash("anything", "/nonexistent.ritz") is False


# ============================================================================
# Build Sig Data Tests
# ============================================================================

class TestBuildSigData:
    """Tests for build_sig_data()."""

    @pytest.mark.unit
    def test_basic_build(self):
        """Builds correct sig data structure."""
        src = "fn foo() -> i32\n    42\n"
        data = build_sig_data(
            source=src,
            fn_hashes={'foo': 'abc123'},
            sig_hashes={'foo': 'sig456'},
            fn_ir={'foo': 'define i32 @foo() { ret i32 42 }'},
            imports=['ritzlib.sys'],
        )
        assert data['source_hash'] == source_file_hash(src)
        assert data['functions']['foo']['hash'] == 'abc123'
        assert data['functions']['foo']['sig_hash'] == 'sig456'
        assert data['functions']['foo']['ir'] == 'define i32 @foo() { ret i32 42 }'
        assert data['imports'] == ['ritzlib.sys']

    @pytest.mark.unit
    def test_preserves_old_ir_for_unchanged(self):
        """Preserved cached IR from old sig data for unchanged functions."""
        old_data = {
            'functions': {
                'foo': {'hash': 'abc123', 'ir': 'cached ir for foo'},
            }
        }
        data = build_sig_data(
            source="whatever",
            fn_hashes={'foo': 'abc123'},  # Same hash
            old_sig_data=old_data,
        )
        assert data['functions']['foo']['ir'] == 'cached ir for foo'

    @pytest.mark.unit
    def test_clears_old_ir_for_changed(self):
        """Clears cached IR for functions with changed hash."""
        old_data = {
            'functions': {
                'foo': {'hash': 'old_hash', 'ir': 'stale ir'},
            }
        }
        data = build_sig_data(
            source="whatever",
            fn_hashes={'foo': 'new_hash'},  # Different hash
            old_sig_data=old_data,
        )
        assert data['functions']['foo']['ir'] == ''


# ============================================================================
# Signature Change Detection Tests
# ============================================================================

class TestDetectSigChanges:
    """Tests for detect_sig_changes()."""

    @pytest.mark.unit
    def test_no_old_cache(self):
        """All sigs are 'changed' when no old cache exists."""
        changes = detect_sig_changes(
            "/nonexistent.ritz",
            {'foo': 'hash1', 'bar': 'hash2'},
        )
        assert set(changes) == {'foo', 'bar'}

    @pytest.mark.unit
    def test_no_changes(self):
        """No changes when all sig hashes match."""
        with tempfile.NamedTemporaryFile(suffix='.ritz', delete=False) as f:
            source_path = f.name

        try:
            data = {
                'source_hash': 'x',
                'functions': {
                    'foo': {'hash': 'h1', 'sig_hash': 'sig1'},
                    'bar': {'hash': 'h2', 'sig_hash': 'sig2'},
                },
                'imports': [],
            }
            write_sig_file(source_path, data)
            changes = detect_sig_changes(source_path, {'foo': 'sig1', 'bar': 'sig2'})
            assert changes == []
        finally:
            Path(source_path).unlink(missing_ok=True)
            _sig_path(source_path).unlink(missing_ok=True)

    @pytest.mark.unit
    def test_sig_changed(self):
        """Detects when a function's signature hash changed."""
        with tempfile.NamedTemporaryFile(suffix='.ritz', delete=False) as f:
            source_path = f.name

        try:
            data = {
                'source_hash': 'x',
                'functions': {
                    'foo': {'hash': 'h1', 'sig_hash': 'old_sig'},
                },
                'imports': [],
            }
            write_sig_file(source_path, data)
            changes = detect_sig_changes(source_path, {'foo': 'new_sig'})
            assert 'foo' in changes
        finally:
            Path(source_path).unlink(missing_ok=True)
            _sig_path(source_path).unlink(missing_ok=True)


# ============================================================================
# Path to Import Name Tests
# ============================================================================

class TestPathToImportName:
    """Tests for _path_to_import_name()."""

    @pytest.mark.unit
    def test_ritzlib_module(self):
        """Converts ritzlib path to import name."""
        result = _path_to_import_name("/project/ritzlib/sys.ritz", "/project")
        assert result == "ritzlib.sys"

    @pytest.mark.unit
    def test_nested_ritzlib_module(self):
        """Converts nested ritzlib path to import name."""
        result = _path_to_import_name("/project/ritzlib/async/runtime.ritz", "/project")
        assert result == "ritzlib.async.runtime"

    @pytest.mark.unit
    def test_fallback_ritzlib_detection(self):
        """Falls back to detecting 'ritzlib' in path."""
        result = _path_to_import_name("/some/path/ritzlib/io.ritz")
        assert result == "ritzlib.io"


# ============================================================================
# Integration Test: Full Round-Trip
# ============================================================================

class TestFullRoundTrip:
    """Integration tests for the complete cache flow."""

    @pytest.mark.integration
    def test_build_write_read_check(self):
        """Full round-trip: build hashes, write sig, read back, check cache."""
        src = "fn foo() -> i32\n    42\n\nfn bar() -> i32\n    99\n"

        with tempfile.NamedTemporaryFile(suffix='.ritz', delete=False, mode='w') as f:
            f.write(src)
            source_path = f.name

        try:
            # Build hash map
            hm = build_hash_map(src, source_path)
            assert 'foo' in hm
            assert 'bar' in hm

            # Build and write sig data
            sig_data = build_sig_data(
                source=src,
                fn_hashes=hm,
                fn_ir={'foo': 'define i32 @foo() { ret i32 42 }'},
            )
            write_sig_file(source_path, sig_data)

            # Read back
            read_back = read_sig_file(source_path)
            assert read_back is not None

            # Check cache - should be all hits
            hits, misses = check_cache(hm, read_back)
            assert len(hits) == 2
            assert len(misses) == 0

            # Source hash should match
            assert check_source_hash(src, source_path) is True

            # Modify one function
            src2 = "fn foo() -> i32\n    42\n\nfn bar() -> i32\n    100\n"
            hm2 = build_hash_map(src2, source_path)
            hits2, misses2 = check_cache(hm2, read_back)
            assert 'foo' in hits2
            assert 'bar' in misses2

            # Source hash should NOT match anymore
            assert check_source_hash(src2, source_path) is False

        finally:
            Path(source_path).unlink(missing_ok=True)
            _sig_path(source_path).unlink(missing_ok=True)
