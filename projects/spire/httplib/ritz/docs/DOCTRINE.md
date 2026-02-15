# Ritz Language Development Doctrine

Core principles that guide development decisions on the Ritz language.

---

## No Concessions Doctrine

> **"Never make concessions for the language - we are MAKING the language."**

When developing a language, we define what is possible. Working around language limitations while defining them is backwards thinking.

**Anti-patterns:**
- Renaming functions to avoid a parser bug
- Using numeric literals because constant imports don't work
- Adding special cases for "known broken" patterns
- Documenting workarounds instead of fixing root causes

**Correct approach:**
- Fix the underlying issue
- The language serves users, not the other way around
- If something doesn't work, it's a bug to be fixed, not a limitation to accept

---

## Ghost Doctrine

> **"Warnings are the ghosts of future production outages. Fix them now or be haunted later."**

This extends beyond warnings to any observed anomaly:
- Compiler warnings
- Test flakiness
- "Weird" behavior that "works for now"
- Edge cases that "shouldn't happen in practice"

**Application:**
- A bug that silently corrupts state will manifest in mysterious ways later
- Fix anomalies when discovered, not when they become critical
- Track issues properly - don't let them become folklore

---

## Test-Driven Development

The ritz project follows strict TDD:
1. Write failing tests first
2. Implement to make tests pass
3. Refactor with confidence
4. All examples must pass before moving forward

---

## Bootstrap Philosophy

> **"Iterate rapidly in Python until design stabilizes, then self-host."**

- ritz0 (Python) is the bootstrap compiler - flexibility over performance
- ritz1 (Ritz) is the self-hosted compiler - the real implementation
- Both must produce identical output for the same input
- Self-hosting is the ultimate validation of language design

---

## Issue Tracking

Bugs discovered during development MUST be tracked:
- Create GitHub issues for non-trivial bugs
- Include reproduction steps
- Document the investigation done
- Don't rely on memory or TODO comments

---

*Last updated: 2024-12-26*
