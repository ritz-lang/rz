# Ritz Language Project Structure

**Last Updated**: 2024-12-23 (Session 2)
**Current Status**: Phase 3 - Self-Hosting Bootstrap (In Progress)

---

## Directory Layout

```
langdev/
├── ritz0/                          # Bootstrap Compiler (Python)
│   ├── lexer.py                    # ✅ Tokenization (28 unit tests)
│   ├── tokens.py                   # ✅ Token definitions
│   ├── parser.py                   # ✅ Recursive descent parser (39 unit tests)
│   ├── ritz_ast.py                 # ✅ AST node definitions
│   ├── emitter_llvmlite.py         # ✅ LLVM IR generation
│   ├── ritz0.py                    # ✅ CLI driver with multi-file support
│   ├── test/                       # ✅ Unit test suite (67 tests)
│   │   ├── test_lexer.py
│   │   ├── test_parser.py
│   │   └── ...
│   └── README.md                   # Bootstrap implementation notes
│
├── ritz1/                          # Self-Hosted Compiler (Ritz)
│   ├── src/
│   │   ├── lexer.ritz              # ✅ Ritz lexer implementation (6/6 tests)
│   │   ├── nfa.ritz                # ✅ NFA engine (12/12 tests)
│   │   ├── utf8.ritz               # ✅ UTF-8 decoder with test support
│   │   ├── tokens.ritz             # ✅ Token constant definitions
│   │   ├── regex.ritz              # 📋 Regex parser skeleton (design phase)
│   │   ├── parser.ritz             # ⏳ Parser (next to implement)
│   │   └── emitter.ritz            # ⏳ LLVM IR emitter (after parser)
│   │
│   ├── test/
│   │   ├── test_lexer.ritz         # ✅ Lexer tests (6 tests)
│   │   ├── test_nfa.ritz           # ✅ NFA engine tests (12 tests)
│   │   ├── test_utf8.ritz          # ✅ UTF-8 decoder tests
│   │   ├── test_thompson.ritz      # ✅ Thompson construction tests
│   │   ├── test_parser.ritz        # ⏳ Parser tests (to be created)
│   │   └── test_emitter.ritz       # ⏳ Emitter tests (to be created)
│   │
│   └── TOKENS.md                   # 📋 Token DSL specification
│
├── examples/                       # ✅ Working example programs
│   ├── 01_hello/
│   ├── 02_exitcode/
│   ├── 03_echo/
│   ├── 04_true_false/
│   ├── 05_cat/
│   ├── 06_head/
│   ├── 07_wc/
│   ├── 08_seq/
│   ├── 09_yes/
│   └── 10_sleep/
│
├── docs/                           # Documentation
│   ├── DESIGN.md                   # ✅ Language design & syntax
│   ├── BOOTSTRAP.md                # ✅ Bootstrap strategy
│   ├── CLI.md                      # ✅ Command-line interface
│   ├── PACKAGING.md                # ✅ Package structure
│   ├── TESTING.md                  # ✅ Testing framework
│   ├── EXAMPLES.md                 # ✅ 70 example programs (planned)
│   ├── RITZLIB.md                  # ✅ Standard library overview
│   ├── CONCURRENCY.md              # ✅ Async/concurrency design
│   ├── TOKEN_DSL.md                # 📋 Token DSL specification (NEW)
│   └── TOKEN_DSL_IMPLEMENTATION.md # 📋 Implementation plan (NEW)
│
├── build/                          # Build outputs
│   └── (artifacts from make build)
│
├── test/                           # Phase 1 language tests
│   ├── test_level1.ritz            # ✅ 12/12 tests
│   ├── test_level2.ritz            # ✅ 7/7 tests
│   ├── test_level3.ritz            # ✅ 11/11 tests
│   ├── test_level4.ritz            # ✅ 12/12 tests
│   ├── test_level5.ritz            # ✅ 4/4 tests
│   └── test_level6.ritz            # ✅ 3/3 tests
│
├── Makefile                        # ✅ Build system
├── build.py                        # ✅ Build script
│
├── CURRENT_STATUS.md               # ✅ Current project status
├── DONE.md                         # ✅ Completion history
├── SESSION_2_SUMMARY.md            # ✅ This session summary
├── SESSION_CONTINUATION_SUMMARY.md # ✅ Previous session recap
├── PHASE_3_LEXER_ANALYSIS.md       # 📋 DSL vs Manual decision
├── NEXT_SESSION_GUIDE.md           # 📋 Parser implementation guide
├── PROJECT_STRUCTURE.md            # 📋 This file
└── README.md                       # Project overview

```

---

## Component Status

### ✅ Completed & Stable

#### ritz0 (Bootstrap Compiler)
- **Lexer**: 28 unit tests passing
- **Parser**: 39 unit tests passing
- **Emitter**: Generates valid LLVM IR
- **CLI**: Full command-line interface
- **Total Code**: ~2000 lines of Python

#### Phase 1 Examples (10 Working Programs)
- 01_hello: Basic output
- 02_exitcode: Return codes
- 03_echo: Arguments processing
- 04_true_false: Exit codes
- 05_cat: File I/O
- 06_head: Line-limited output
- 07_wc: Word/line counting
- 08_seq: Number sequences
- 09_yes: String repetition
- 10_sleep: System calls (nanosleep)

#### Phase 3 Lexer (ritz1)
- **Basic Lexer**: 6 unit tests passing
- **NFA Engine**: 12 integration tests passing
- **UTF-8 Decoder**: Correct handling of multi-byte sequences
- **Thompson Construction**: Full NFA building support

### ⏳ In Progress (Critical Path)

#### ritz1 Parser
- **Status**: Ready to implement
- **Effort**: 3-4 days
- **Blocker**: None - all prerequisites done
- **Next**: Session 3

#### ritz1 Emitter
- **Status**: Ready to design
- **Effort**: 3-4 days
- **Blocker**: Waiting for parser completion
- **Next**: Session 4

### 📋 Designed (Post-Bootstrap)

#### Token DSL
- **Status**: Fully designed and documented
- **Effort**: 4-5 days
- **Blocker**: None - post-bootstrap work
- **Files**: TOKEN_DSL.md, TOKEN_DSL_IMPLEMENTATION.md
- **Next**: Phase 4

---

## Test Statistics

### Test Coverage Summary

```
Component              Tests    Status    Pass Rate
─────────────────────────────────────────────────────
ritz0 Unit Tests       67       ✅ Pass   100%
ritz0 Language Tests   49       ✅ Pass   100%
ritz1 Lexer Tests      6        ✅ Pass   100%
ritz1 NFA Tests        12       ✅ Pass   100%
────────────────────────────────────────────────────
TOTAL                  134      ✅ Pass   100%
```

### Test Breakdown by Type

| Type | Count | Examples |
|------|-------|----------|
| **Unit Tests** (ritz0 implementation) | 67 | Lexer, Parser |
| **Language Tests** (Ritz compilation) | 49 | Phase 1 test levels |
| **Module Tests** (NFA/UTF-8) | 18 | Lexer, NFA, UTF-8 |
| **Integration Tests** | N/A | Examples 01-10 |
| **E2E Bootstrap Tests** | Planned | ritz0→ritz1 chain |

---

## Build & Test Commands

### Full Test Suite
```bash
make                          # Run all tests
make test                     # Same as above
```

### Component Tests
```bash
make unit                     # Python unit tests only (ritz0)
make ritz                     # Ritz language tests (ritz1)
make examples                 # Build and test all examples
```

### Individual Tests
```bash
make test-01_hello            # Test hello example
make build-05_cat             # Build cat example
make test-ritz1-lexer         # Test ritz1 lexer
make test-ritz1-nfa           # Test ritz1 NFA
```

### Compilation
```bash
python ritz0/ritz0.py <source.ritz> -o <output.ll>
llc <output.ll> -o <output.o>
gcc <output.o> -o <binary>
```

---

## Critical Path Timeline

### Current (Session 2): Design ✅
- ✅ Token DSL completely designed
- ✅ Critical decision made (manual vs DSL)
- ✅ Documentation created
- ✅ Ready for parser implementation

### Session 3: Parser (3-4 days)
- ⏳ Design parser test suite
- ⏳ Implement recursive descent parser
- ⏳ All parser tests passing
- 🎯 Unblock emitter work

### Session 4: Emitter (3-4 days)
- ⏳ Design emitter test suite
- ⏳ Implement LLVM IR generation
- ⏳ All emitter tests passing
- 🎯 Unblock bootstrap

### Session 5: Bootstrap (1-2 days)
- ⏳ Get ritz0 to compile ritz1
- ⏳ Get ritz1 to compile itself
- ⏳ Verify Phase 1 examples work
- 🎯 **Self-hosting achieved!**

### Sessions 6+: Enhancement (4-5 days)
- ⏳ Token DSL implementation
- ⏳ Lexer rewrite with DSL
- ⏳ Performance optimization

---

## Key Design Decisions

### Decision 1: Use Integer Constants for Token Types
**Rationale**: Enums not yet supported in language
**Status**: ✅ Working perfectly
**Location**: ritz1/src/tokens.ritz

### Decision 2: Manual NFA Lexer vs Token DSL
**Chosen**: Manual NFA for Phase 3 (bootstrap)
**Alternative**: Token DSL (deferred to Phase 4)
**Rationale**: No timeline impact, critical path focused
**Documentation**: PHASE_3_LEXER_ANALYSIS.md

### Decision 3: Multi-File Testing Support
**Implementation**: Added --lib flag to ritz0.py
**Benefit**: Modular code organization
**Status**: ✅ Working with Phase 3 lexer tests

### Decision 4: Recursive Descent + Pratt Parsing
**Chosen**: Same approach as ritz0
**Benefit**: Proven pattern, easy to translate
**Status**: ⏳ Ready to implement in Session 3

---

## Code Quality Metrics

### Lines of Code
- **ritz0**: ~2000 lines (Python)
- **ritz1 Lexer**: ~200 lines (Ritz)
- **ritz1 NFA**: ~400 lines (Ritz)
- **ritz1 Parser**: ~500 lines planned (Ritz)
- **ritz1 Emitter**: ~1000 lines planned (Ritz)

### Test Coverage
- **ritz0**: 67 unit tests + 49 language tests
- **ritz1**: 6 lexer + 12 NFA tests (comprehensive)
- **Overall**: 134/134 tests passing (100%)

### Documentation
- **Design Docs**: 5 files (~2000 lines)
- **Implementation Guides**: 3 files (~800 lines)
- **Code Comments**: Inline throughout

---

## Development Workflow

### Typical Session Flow
1. **Plan** (10 min)
   - Review CURRENT_STATUS.md
   - Check git log for context
   - Read NEXT_SESSION_GUIDE.md

2. **Implement** (2-4 hours)
   - Test-driven development
   - Incremental progress
   - Frequent commits

3. **Verify** (30 min)
   - Run full test suite
   - Check git status
   - Update documentation

4. **Document** (30 min)
   - Update CURRENT_STATUS.md
   - Create session summary
   - Commit everything

### Git Workflow
```bash
# Start of session
git status                    # Verify clean
git log --oneline | head -5  # Recent history

# During development
git add <modified files>
git commit -m "Component: description"

# End of session
git status                    # Verify clean
make test                     # Final verification
git log --oneline | head -10  # See progress
```

---

## Key Files for Navigation

### For Understanding Current Status
1. `CURRENT_STATUS.md` - Start here for overview
2. `SESSION_2_SUMMARY.md` - Recent progress
3. `PROJECT_STRUCTURE.md` - This file

### For Implementation Work
1. `NEXT_SESSION_GUIDE.md` - Detailed implementation guide
2. `ritz0/parser.py` - Reference implementation
3. `ritz1/test/test_lexer.ritz` - Test patterns

### For Understanding Design
1. `docs/DESIGN.md` - Language syntax and semantics
2. `docs/BOOTSTRAP.md` - Bootstrap strategy
3. `PHASE_3_LEXER_ANALYSIS.md` - Decision framework

### For Phase 4 Planning
1. `docs/TOKEN_DSL.md` - DSL specification
2. `docs/TOKEN_DSL_IMPLEMENTATION.md` - Implementation plan
3. `ritz1/TOKENS.md` - Token definitions

---

## Quick Reference

### Running Tests
```bash
make                   # All tests
make unit              # Python tests only
make ritz              # Ritz tests only
make test-<example>    # Specific example
```

### Building Examples
```bash
make build-<example>   # Compile example
make test-<example>    # Compile + test
make list              # List all examples
```

### Creating New Tests
1. Create test file in appropriate directory
2. Add @test attribute to test functions
3. Run: `make test`
4. All tests must return 0 for success

### Viewing Project History
```bash
git log --oneline      # Condensed history
git log -p <file>      # Changes to file
git diff HEAD~1        # Changes since last commit
git status             # Uncommitted changes
```

---

## Success Criteria (Phase 3)

- [ ] **Parser Complete**
  - All parser tests passing
  - Handles all language constructs
  - Ready for emitter

- [ ] **Emitter Complete**
  - All emitter tests passing
  - Generates correct LLVM IR
  - Bootstrapping ready

- [ ] **Bootstrap Successful**
  - ritz0 → ritz1.ll works
  - ritz1.ll → binary works
  - ritz1 → ritz1 works (self-hosting!)
  - All Phase 1 examples compile

- [ ] **Documentation Complete**
  - All work documented
  - Clear session summaries
  - Ready for Phase 4

---

## Conclusion

The Ritz project is well-organized with:
- ✅ Clear component separation
- ✅ Comprehensive documentation
- ✅ High test coverage (100%)
- ✅ Clean git history
- ✅ Well-defined next steps

**Current Status**: Ready for parser implementation

**Estimated Time to Self-Hosting**: 2 weeks

---

*Document Version*: 2.0
*Last Updated*: 2024-12-23
*Status*: Phase 3 In Progress
