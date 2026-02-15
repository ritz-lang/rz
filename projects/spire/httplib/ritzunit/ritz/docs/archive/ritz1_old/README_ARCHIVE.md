# ritz1_old - Archived Original Self-Hosting Attempt

This directory contains the **original ritz1 self-hosting compiler** that was developed in earlier phases. It has been archived and replaced with the new incremental approach.

## What's Here

This was the first attempt at building a self-hosted Ritz compiler:

- **src/** - Full compiler implementation (~7768 lines across 17 files)
  - Lexer with NFA-based tokenization
  - Parser with recursive descent + Pratt parsing
  - Type checker (54 tests)
  - Borrow checker (21 tests)
  - IR emitter with magic byte offsets (the blocker!)
- **test/** - Compiler test suite
- **Makefile** - Build system for the old approach

## Why Archived?

**Blockers:**
1. `grammar.ritz` uses a DSL that ritz0 can't parse
2. `emitter.ritz` uses magic struct offsets (Issue #3)
3. 7768 lines - too complex to bootstrap all at once

**The New Approach:**
The new `ritz1/` (formerly ritz1_mini) takes an incremental approach:
- Starts minimal (298 lines)
- Uses ritz1/ir backend (no magic offsets!)
- Grows feature-by-feature
- A/B tested at every step

## What Was Learned

This attempt taught us:
- ✅ How to build lexer/parser in Ritz
- ✅ Type system design
- ✅ Borrow checker fundamentals
- ❌ Magic offsets are a dead end
- ❌ Grammar DSL adds unnecessary complexity
- ✅ Incremental validation is key

## Value of This Code

This code is **not wasted** - it's a reference implementation! When building the new ritz1:
- Lexer design can be adapted (without the DSL)
- Parser patterns are proven
- Type checker logic is sound
- We know what NOT to do (magic offsets!)

## History

- Created: Early phases of Ritz development
- Archived: December 24, 2024
- Replaced by: New incremental ritz1 (in `ritz1/`)

The journey continues with a better foundation! 🚀
