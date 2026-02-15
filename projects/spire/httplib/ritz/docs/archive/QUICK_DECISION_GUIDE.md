# Phase 3 Quick Decision Guide

## The Question
How should we represent TokenType for the ritz1 self-hosted lexer?

## Your Two Options

### 🏃 Option B: Integer Constants (FAST PATH)
```ritz
const TOKEN_INT: i32 = 0
const TOKEN_STRING: i32 = 1
const TOKEN_IDENT: i32 = 2
// ... 40+ more token types

struct Token
  kind: i32      // Token type constant
  value: *i8
  line: i32
  col: i32
```

**⏱️ Time to Phase 3**: Immediate (0 hours)
**📈 Complexity**: Low
**✨ Ergonomics**: Acceptable (if/else chains)
**🎯 Phase 4 Plan**: Add proper enums in ritz2

---

### 🏗️ Option A: Full Enum Support (COMPLETE PATH)
```ritz
enum TokenType
  Int, String, Ident, Keyword,
  LParen, RParen, LBrace, RBrace,
  Newline, Indent, Dedent, EOF
  // ... 40+ more variants

struct Token
  kind: TokenType
  value: *i8
  line: i32
  col: i32
```

**⏱️ Time to Phase 3**: +1 week (6-8 hours impl)
**📈 Complexity**: High (tagged unions, pattern matching)
**✨ Ergonomics**: Excellent (Rust-like)
**🎯 Phase 4 Plan**: Use in ritz2 compiler directly

---

## Comparison

| Factor | Option B | Option A |
|--------|----------|----------|
| **Start Phase 3** | This week ✅ | Next week ⏳ |
| **Type Safety** | Weak (i32 abuse) | Strong (enum) |
| **Code Ergonomics** | OK (if/else) | Excellent (match) |
| **Complexity** | Low | High |
| **Bootstrap Risk** | Very Low | Low |
| **Learning Value** | Practical | Educational |

---

## My Recommendation: **Option B**

### Why Option B Wins
1. **Bootstrap Philosophy**: Self-hosting is the goal, enums are a nice-to-have
2. **Constants Work**: i32 is perfectly adequate for token type discrimination
3. **Faster Iteration**: Bootstrap this week → iterate on enums next week
4. **Phase 4 Ready**: ritz2 will be written in ritz, use proper enums there
5. **Pragmatic**: TDD says "add when needed", not "add before needed"

### What You Get
- ✅ ritz1 compiling in 2-3 weeks
- ✅ ritz1 self-hosting bootstrap this month
- ✅ Full enums implemented in Phase 4
- ✅ Faster feedback loop on the compiler design

---

## Decision Checklist

### Before Phase 3 Starts

Choose ONE:
- [ ] **Path A**: Implement enums first (6-8 hours, then Phase 3)
- [ ] **Path B**: Use constants now, enums in Phase 4 (Phase 3 immediately)

Once selected:
- [ ] Create ritz1/ directory structure
- [ ] Design ritz1/lexer.ritz interface
- [ ] Begin lexer implementation

---

## Status Summary

**Current**:
- ✅ Phase 1G: 116/116 tests passing
- ✅ All infrastructure ready
- ✅ Compiler stable
- ✅ Enum analysis complete
- ⏳ Awaiting Phase 3 decision

**When You Decide**:
- Next: Phase 3 ritz1 lexer implementation
- Timeline: 2-3 weeks to self-hosting
- Success metric: ritz0 → ritz1.ll, ritz1 → ritz1 (self-compile)

---

## Questions?

**For Option A details**: See `ENUM_SUPPORT_ANALYSIS.md`
**For Option B details**: See `PHASE_3_PLANNING.md`
**For full context**: See `PHASE_3_READINESS.md`

---

## Ready to Proceed?

**Just tell me**:
> "Let's do Option B, start Phase 3 now"

**OR**

> "Let's do Option A, implement enums first"

Then we move forward! 🚀
