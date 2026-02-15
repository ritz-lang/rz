# Cleanup TODO - Project Organization

## 📋 Cleanup Tasks

### 1. Documentation Consolidation

**Move to `docs/archive/`:**
- All SESSION_*.md files (11+ files)
- PHASE_*.md files (6+ files)
- ISSUE_*.md files (3 files)
- Old status files: COMPILER_STATUS.md, BOOTSTRAP_STATUS.md, etc.
- Analysis files: ENUM_SUPPORT_ANALYSIS.md, etc.

**Keep in root:**
- README.md
- TODO.md
- RITZ1_CODE_REVIEW.md (recent, relevant)
- GITHUB_ISSUES.md (recent, relevant)
- RITZ1_PROGRESS.md (current status)

**Move to `docs/`:**
- COMPILER_ARCHITECTURE_OVERVIEW.md
- ROADMAP.md
- EXAMPLES.md (if exists)

### 2. Build Artifacts Cleanup

**Remove:**
- All `.ll` files in root and `/tmp`
- All `.s` files
- All `.o` files
- Test binaries in `/tmp/test_*`

**Add to .gitignore:**
```
*.ll
*.s
*.o
/tmp/test_*
__pycache__/
.pytest_cache/
*.pyc
```

### 3. Test Organization

**Current mess:**
- Random test files in /tmp/
- No organized test structure

**Create structure:**
```
tests/
  ritz0/           # Python bootstrap tests (already exists?)
  ritz1/           # Self-hosted compiler tests
    unit/          # Individual feature tests
    integration/   # Full program tests
    ab/            # A/B comparison tests
```

### 4. Project Structure

**Create ritz.toml:**
```toml
[package]
name = "ritz"
version = "0.1.0"
authors = ["Aaron Sinclair <aaron.sinclair@bettercomp.com>"]
edition = "2024"

[dependencies]
# None yet - we're bootstrapping!

[dev-dependencies]
# Test framework TBD

[[bin]]
name = "ritz0"
path = "ritz0/ritz0.py"

[[bin]]
name = "ritz1"
path = "ritz1/compile.sh"
```

### 5. Scripts Organization

**Create `scripts/` directory:**
- Move test_ab.sh → scripts/ab_test.sh
- Create scripts/build_ritz0.sh
- Create scripts/build_ritz1.sh
- Create scripts/test_all.sh

### 6. Examples Validation

**Verify examples/ structure:**
- Check all Tier 1 examples compile
- Ensure consistent structure
- Add missing tests

## 🎯 Execution Order

1. Create directory structure
2. Move documentation to archives
3. Clean build artifacts
4. Create ritz.toml
5. Organize scripts
6. Update .gitignore
7. Commit cleanup

## 📊 Estimated Time

- Directory creation: 10 min
- File moves: 20 min
- Build cleanup: 5 min
- Script organization: 15 min
- Testing: 30 min
- **Total: ~1.5 hours**
