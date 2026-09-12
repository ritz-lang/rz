# Next Session Roadmap

## Quick Status
- ✅ Debug info fully working (DWARF preserved, GDB functional)
- ✅ CLI tool created and working (`./ritz build|test|run|clean|list`)
- ✅ Build system supports debug artifacts with `-g` flag
- ✅ All 147 compiler tests passing
- ✅ 21_ls refactored as model (641 → 446 lines)
- ✅ 30 working utilities (Tiers 1-3 complete)

## Recommended Next Task: Issue #38
**Refactor remaining 29 examples to use ritzlib imports**

### Why This?
- Clear model exists (21_ls)
- Straightforward mechanical refactoring
- High value: ~30% code reduction per example
- No new language features needed
- Improves code quality and maintainability

### Process
1. Pick an example (22_mkdir is good start: 215 lines)
2. Follow 21_ls pattern:
   - Replace `extern fn syscall*` with `import ritzlib.sys`
   - Replace inline functions with imports
   - Use ritzlib.io, ritzlib.str, ritzlib.fs
   - Use ritzlib.args for argument parsing
3. Verify tests still pass: `./ritz test 22_mkdir`
4. Commit with pattern: `Refactor 22_mkdir to use ritzlib imports`

### Estimated Effort Per Example
- Small (200 lines): 15-20 minutes
- Medium (300 lines): 20-30 minutes
- Large (400+ lines): 30-45 minutes
- Total for all 29: 4-5 hours

### Files to Modify
- `examples/NN_name/src/main.ritz` - Remove inline definitions, add imports
- Other examples follow same pattern

## Alternative Tasks (If You Prefer)

### Issue #33: Add for loop support
- Parser already recognizes `ForStmt`
- Emitter needs `isinstance(stmt, ForStmt)` handler
- Desugar to while loop with counter
- Estimated: 2-3 hours

### Issue #32: Add bit shift operators
- Add << and >> to lexer
- Add to parser expression handling
- Add LLVM IR generation
- Estimated: 1-2 hours

### Issue #39: Implement native build command
- Much larger: 8-12 hours
- Requires reading/parsing ritz.toml
- Process management for llc/ld.lld
- Worth doing but complex

## Commands Reference

```bash
# Build specific example
./ritz build 22_mkdir

# Build with debug artifacts kept
./ritz build -g 22_mkdir

# Test example
./ritz test 22_mkdir

# Run any .ritz file
./ritz run examples/test.ritz

# List all packages
./ritz list

# Run compiler tests
./ritz ritz-tests

# Clean all build artifacts
./ritz clean
```

## Debug Info Testing

```bash
# View source in disassembly
objdump -S examples/22_mkdir/mkdir

# List with debug info
readelf --debug-dump=info build/mkdir.o | head -20

# Debug with GDB
gdb ./examples/22_mkdir/mkdir
(gdb) list main
(gdb) break main
(gdb) run
```

## Key Files to Know

- **ritz0/emitter_llvmlite.py** - LLVM IR generation
- **ritz0/ritz0.py** - Main compiler entry point
- **build.py** - Python build system
- **ritz** - CLI wrapper (executable)
- **ritzlib/*.ritz** - Standard library modules
- **examples/21_ls/** - Model for refactoring

## Troubleshooting

If tests fail after changes:

```bash
# Check compilation
./ritz build 22_mkdir 2>&1 | grep Error

# Keep debug artifacts for inspection
./ritz build -g 22_mkdir

# Look at generated LLVM IR
cat build/mkdir.ll | less

# Look at generated object file
objdump -d build/mkdir.o | less
```

## Session Notes

- All work is committed and pushed to origin/main
- GitHub issues are created and tracked
- Documentation in DONE.md tracks completed work
- Use CLAUDE.md for complex architectural questions

Good luck! 🎭
