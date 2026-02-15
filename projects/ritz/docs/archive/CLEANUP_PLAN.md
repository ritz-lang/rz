# Phase 5: Project Cleanup and Preparation for ritz2

**Status**: Cleanup plan defined, ready for execution
**Created**: December 25, 2024
**Related**: CODE_REVIEW_RITZ1.md (comprehensive code review)

## Overview

This document outlines the cleanup and preparation phase needed before continuing with example programs (Phase 6) and ritz2 development (Phase 7+).

## GitHub Issues Created

The following issues have been created to track all work items:

### Critical Path (Blocking)
1. **Issue #8**: Phase 5: Implement multi-argument function calls
   - Status: OPEN
   - Priority: Medium
   - Blocks: Complex real-world programs

2. **Issue #9**: Fix string literal parsing (NFA pattern hang)
   - Status: OPEN
   - Priority: Medium
   - Blocks: String output, I/O examples

### Documentation and Structure
3. **Issue #11**: Clean up project structure and remove deprecated files
   - Status: OPEN
   - Priority: High
   - Impact: Code organization and maintainability

4. **Issue #12**: Implement ritz.toml packaging format
   - Status: OPEN
   - Priority: High
   - Impact: Build system infrastructure

### User Experience
5. **Issue #10**: Add comprehensive error reporting with line/column information
   - Status: OPEN
   - Priority: Medium
   - Impact: Developer experience

### Testing Infrastructure
6. **Issue #14**: Create comprehensive test suite for ritz1
   - Status: OPEN
   - Priority: High
   - Impact: Quality assurance and examples

### Optimization (Lower Priority)
7. **Issue #13**: Optimize variable lookup with hash table
   - Status: OPEN
   - Priority: Low
   - Impact: Performance for large programs

## Execution Plan

### Phase 5A: Immediate Cleanup (This Week)
**Goal**: Clean codebase, organize documentation

#### 1. Remove Deprecated Files
- [ ] Delete ritz1/src/allocator_simple.ritz (superseded by parser heap)
- [ ] Delete ritz1/src/main.ritz (superseded by main_new.ritz)
- [ ] Delete ritz1/src/compile_all.ritz (unused)
- [ ] Clean build/ directory artifacts
- [ ] Update .gitignore to exclude build artifacts

**Effort**: 1 hour
**PR**: Single commit "cleanup: remove deprecated files"

#### 2. Reorganize Documentation
- [ ] Create docs/ directory structure:
  ```
  docs/
  ├── README.md (from project root)
  ├── ARCHITECTURE.md (from COMPILER_ARCHITECTURE_OVERVIEW.md)
  ├── BOOTSTRAP.md (from BOOTSTRAP_STATUS.md)
  ├── LIMITATIONS.md (new - from CODE_REVIEW_RITZ1.md)
  ├── TESTING.md (new - test methodology)
  ├── EXAMPLES.md (new - example programs)
  ├── RITZ_TOML.md (new - packaging format)
  └── archive/
      ├── ENUM_*.md
      ├── ISSUE_*.md
      ├── PHASE_*.md
      ├── SESSION_*.md
      └── (all investigation notes)
  ```
- [ ] Create docs/LIMITATIONS.md documenting all known issues
- [ ] Verify all links point to correct locations

**Effort**: 2 hours
**PRs**:
  - "docs: move core documentation to docs/ directory"
  - "docs: archive investigation notes to docs/archive/"
  - "docs: create LIMITATIONS.md with all known issues"

#### 3. Create RITZ_TOML Specification
- [ ] Design ritz.toml format (docs/RITZ_TOML.md)
  - Package metadata (name, version, description)
  - Build configuration (main file, output path)
  - Test configuration (test files, expected outputs)
  - Dependencies (for future use)
- [ ] Create example ritz.toml files
- [ ] Document best practices

**Effort**: 2 hours
**PR**: "docs: add ritz.toml specification and examples"

**Total Phase 5A**: ~5 hours, 4 PRs

### Phase 5B: String Literals and Multi-Arg (1-2 Weeks)
**Goal**: Close critical feature gaps

#### 4. Fix String Literal Parsing (Issue #9)
- [ ] Debug NFA hang with `[^"]*` pattern
- [ ] Fix kleene star + negation handling in nfa.ritz
- [ ] Re-enable string pattern in lexer_setup.ritz
- [ ] Add escape sequence handling (\n, \t, \", \\)
- [ ] Create test cases for string parsing
- [ ] A/B test string output examples

**Effort**: 3-4 hours
**Related**: Issue #9

#### 5. Implement Multi-Argument Functions (Issue #8)
- [ ] Extend parser_parse_primary to parse comma-separated args
- [ ] Update Expr struct if needed for multiple args
- [ ] Verify IR emission already handles multi-args
- [ ] Create test cases (2-arg, 3-arg, nested calls)
- [ ] A/B test multi-arg function calls

**Effort**: 2-3 hours
**Related**: Issue #8

**Total Phase 5B**: ~6 hours, 2 PRs

### Phase 5C: Error Handling and Testing (1 Week)
**Goal**: Improve developer experience and code quality

#### 6. Add Line/Column Tracking (Issue #10)
- [ ] Add line/col fields to Token struct
- [ ] Update lexer to track line/column during tokenization
- [ ] Implement error reporting in parser
- [ ] Create example error messages
- [ ] Test error cases

**Effort**: 3 hours
**Related**: Issue #10

#### 7. Create Test Suite (Issue #14)
- [ ] Parser unit tests (test_parser.ritz)
- [ ] Lexer unit tests (test_lexer.ritz)
- [ ] Tier 1 example programs
  - hello.ritz
  - simple_math.ritz
  - variables.ritz
  - function.ritz
- [ ] Tier 2 example programs
  - fibonacci.ritz
  - loops.ritz
  - conditions.ritz
- [ ] Run A/B tests on all examples
- [ ] Document test results in docs/EXAMPLES.md

**Effort**: 4-5 hours
**Related**: Issue #14

**Total Phase 5C**: ~7 hours, 3 PRs

### Phase 5D: Packaging and Build System (1 Week)
**Goal**: Enable proper project configuration and testing

#### 8. Implement ritz.toml Parser
- [ ] Create tools/toml_parser.py
  - Parse ritz.toml files
  - Validate configuration
  - Provide helpful error messages
- [ ] Test with example ritz.toml files

**Effort**: 2-3 hours
**Related**: Issue #12

#### 9. Integrate ritz.toml with build.py
- [ ] Update build.py to read ritz.toml
- [ ] Implement `ritz build` command
- [ ] Implement `ritz test` command
- [ ] Support for:
  - Building from ritz.toml configuration
  - Running test cases
  - Generating test reports

**Effort**: 2-3 hours
**Related**: Issue #12

**Total Phase 5D**: ~5 hours, 2 PRs

### Phase 5E: Optimization (Optional)
**Goal**: Improve compiler performance for larger programs

#### 10. Hash Table Variable Lookup (Issue #13)
- [ ] Implement hash_table.ritz with hash function and lookup
- [ ] Integrate with VarMap in main_new.ritz
- [ ] Benchmark performance
- [ ] Ensure no regression in A/B tests

**Effort**: 2-3 hours (optional)
**Related**: Issue #13

---

## Work Schedule

### This Week (Dec 25-27)
- **Phase 5A**: Cleanup and documentation
  - Remove deprecated files
  - Reorganize docs/ directory
  - Create LIMITATIONS.md

### Next Week (Dec 30-Jan 3)
- **Phase 5B**: Critical features
  - Fix string literals
  - Implement multi-arg functions

### Following Week (Jan 6-10)
- **Phase 5C**: Error handling and testing
  - Add line/column tracking
  - Create test suite and examples
  - Run A/B tests

### Week After (Jan 13-17)
- **Phase 5D**: Build system
  - Implement ritz.toml parser
  - Integrate with build.py

### Final Week (Jan 20-24)
- **Phase 5E** (optional): Optimization
  - Hash table implementation
  - Performance improvements
- **Review & Stabilize**: Final testing, documentation review

---

## Success Criteria

### Code Quality
- [ ] No deprecated files in source tree
- [ ] All tests passing (unit + integration)
- [ ] No compiler crashes on invalid syntax
- [ ] Error messages helpful with line/column info

### Documentation
- [ ] Clear architecture documentation
- [ ] All limitations documented
- [ ] Example programs well-commented
- [ ] Test methodology documented
- [ ] Build system documented (ritz.toml)

### Features
- [ ] String literals working
- [ ] Multi-argument functions working
- [ ] All Tier 1, 2, 3 examples passing A/B tests
- [ ] ritz.toml support in build system

### Infrastructure
- [ ] CI/CD pipeline ready (optional but good)
- [ ] Reproducible builds
- [ ] Test suite automated
- [ ] Example programs documented

---

## Risk Assessment

### High Risk
1. **NFA Hang Fix** (Issue #9)
   - Complex pattern interaction
   - Mitigation: Detailed investigation already started
   - Fallback: Implement simpler string pattern if needed

2. **Multi-Arg Parser** (Issue #8)
   - Might affect existing single-arg parsing
   - Mitigation: Comprehensive test suite first
   - Fallback: Revert to single-arg if breaks things

### Medium Risk
3. **Project Reorganization** (Issue #11)
   - Could break relative paths in build system
   - Mitigation: Test build after reorganization
   - Fallback: Easy to revert with git

4. **Error Handling** (Issue #10)
   - Requires token struct changes
   - Mitigation: Change carefully, test extensively
   - Fallback: Can keep basic error handling

### Low Risk
5. **ritz.toml Implementation** (Issue #12)
   - Well-defined specification
   - Can iterate on format if needed
   - No impact on compiler itself

---

## Deliverables

### Code
- [ ] ritz1 compiler without deprecated files
- [ ] Parser with multi-arg support
- [ ] Lexer with string literal support
- [ ] ritz.toml parser and integration
- [ ] Comprehensive test suite

### Documentation
- [ ] docs/ directory with organized documentation
- [ ] LIMITATIONS.md with all known issues
- [ ] TESTING.md with test methodology
- [ ] EXAMPLES.md with all example programs and results
- [ ] RITZ_TOML.md with packaging format specification

### Testing
- [ ] Parser unit tests
- [ ] Lexer unit tests
- [ ] 4 Tier 1 examples (all passing A/B tests)
- [ ] 3 Tier 2 examples (all passing A/B tests)
- [ ] Test report with results

### Build System
- [ ] ritz.toml parser implementation
- [ ] Integration with build.py
- [ ] `ritz build` command working
- [ ] `ritz test` command working
- [ ] Example ritz.toml configurations

---

## Metrics

### Code Quality
- Deprecated files: 55+ .md files → organized
- Test coverage: Parser/Lexer 0% → >80%
- Error reporting: Silent → helpful messages with locations
- Build system: Manual → configuration-driven (ritz.toml)

### Performance
- Variable lookup: O(n) linear → O(1) hash (optional)

### Completion Target
- **Duration**: 4-5 weeks
- **Effort**: ~30 hours development
- **Risk Level**: Medium (mostly lower-risk cleanup)
- **Blockers**: Issue #9 (string literals) and Issue #8 (multi-args)

---

## Next Phase: ritz2 Development

Once Phase 5 is complete:

1. **Feature Planning** (Issue #15 - to be created)
   - Analyze which features needed for ritz2
   - Design type system
   - Plan module system
   - Determine bootstrap strategy

2. **ritz2 Architecture** (Issue #16 - to be created)
   - Full type system (i32, i64, i8, arrays, structs, enums)
   - Module/namespace system
   - Library imports
   - Standard library infrastructure

3. **Boostrap Strategy** (Issue #17 - to be created)
   - ritz0 (Python) → compiles ritz1 bootstrap
   - ritz1 bootstrap → compiles ritz1 production
   - ritz1 production → compiles ritz2

---

## Related Documents

- [CODE_REVIEW_RITZ1.md](CODE_REVIEW_RITZ1.md) - Detailed code review with findings
- [COMPILER_ARCHITECTURE_OVERVIEW.md](COMPILER_ARCHITECTURE_OVERVIEW.md) - Architecture details
- [TODO.md](TODO.md) - Master project TODO list

## Questions and Decisions

### Decision: Order of Work
- **Phase 5A first**: Gets cleanup done, unblocks other work
- **Phase 5B second**: Fixes critical limitations early
- **Phase 5C/D in parallel**: Testing and build system can proceed together
- **Phase 5E optional**: Optimization if time permits

### Decision: Backward Compatibility
- Changing parser for multi-arg: Will work with existing single-arg code ✓
- Changing token struct for line/col: No public API impact ✓
- Moving docs: Just reorganization, no code impact ✓

### Decision: Testing Strategy
- A/B testing: Both paths should produce equivalent results ✓
- Unit tests: Before integration tests ✓
- Test examples: Tier 1 → Tier 2 → Tier 3 ✓

---

## Status: READY TO EXECUTE

All planning complete. Ready to begin Phase 5A cleanup this week.

See GitHub issues #8-14 for detailed task definitions.
