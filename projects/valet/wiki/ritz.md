# The Ritz Language

Ritz is a systems programming language with no libc dependency, compiled to
LLVM IR.  Direct Linux syscalls only.

## Highlights

- Self-hosted compiler (`ritz1` builds itself)
- Ownership + borrow semantics
- StrView for length-tagged string spans (no NUL termination required)
- io_uring async runtime (used by valet)
- Standard library written entirely in Ritz

## Hello World

    fn main() -> i32
        print("Hello, World!\n")
        0
