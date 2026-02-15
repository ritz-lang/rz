# LARB - Language and Architecture Review Board

LARB is the overarching design direction and implementation planning repository for the **Ritz programming language ecosystem**. This repository serves as:

1. **Language Specification** - Authoritative documentation of Ritz syntax, semantics, and behavior
2. **Architecture Review** - Design decisions, RFCs, and architectural guidance
3. **Ecosystem Coordination** - Version standards across Ritz projects via git submodules
4. **Agent Context** - Minimal, efficient references for AI agents to work productively

## Quick Links

- [Language Quick Reference](docs/QUICK_REFERENCE.md) - Minimal context for productive agents
- [Language Specification](docs/LANGUAGE_SPEC.md) - Complete language documentation
- [Ecosystem Overview](docs/ECOSYSTEM.md) - All Ritz projects explained
- [Open Issues & Roadmap](docs/ROADMAP.md) - What needs to be done next
- [LSP Server Requirements](docs/LSP_REQUIREMENTS.md) - Language server protocol spec

## Ritz Ecosystem Projects

| Project | Description | Status |
|---------|-------------|--------|
| [ritz](projects/ritz) | Core compiler (ritz0 Python, ritz1 Ritz) | Active - 324 tests |
| [ritzunit](projects/ritzunit) | Unit testing framework | Active - ELF self-discovery |
| [squeeze](projects/squeeze) | Compression library (gzip/deflate) | Active - 132 tests |
| [valet](projects/valet) | HTTP/1.1 server (1.47M req/sec) | Active - 85 tests |
| [cryptosec](projects/cryptosec) | Cryptographic primitives | Active - 331 tests |

## Design Principles

1. **Minimal syntax, big library** - Python-style indentation, no semicolons or braces
2. **Type-safe with inference** - Static types with extensive type inference
3. **Ownership without annotations** - Rust semantics with simpler surface syntax
4. **One language for everything** - From kernel to script, same syntax
5. **Bootstrappable** - Self-hosting compiler shipped as LLVM IR

## Repository Structure

```
larb/
├── docs/                   # Primary documentation
│   ├── QUICK_REFERENCE.md  # Agent-optimized language summary
│   ├── LANGUAGE_SPEC.md    # Full language specification
│   ├── ECOSYSTEM.md        # Project descriptions and relationships
│   ├── ROADMAP.md          # Open issues and priorities
│   └── LSP_REQUIREMENTS.md # Language server requirements
├── specs/                  # Formal specifications and RFCs
│   └── rfcs/               # Request for Comments
├── projects/               # Git submodules to ecosystem projects
│   ├── ritz/               # Core compiler
│   ├── ritzunit/           # Test framework
│   ├── squeeze/            # Compression library
│   ├── valet/              # HTTP server
│   └── cryptosec/          # Crypto library
├── TODO.md                 # Current work items
└── DONE.md                 # Completed milestones
```

## Getting Started

```bash
# Clone with submodules
git clone --recursive https://github.com/ritz-lang/larb.git

# Or initialize submodules after clone
git submodule update --init --recursive
```

## Standards Versioning

LARB uses git tags to mark ecosystem-wide standards:

- `v0.1.0` - Initial language spec with basic features
- `v0.2.0` - Generics, ownership, and async (current)
- `v1.0.0` - Self-hosting compiler (future)

Each tag ensures all submodule projects conform to that version of the language specification.

## Contributing

Design discussions happen in GitHub Issues and Discussions. Code contributions go to the individual project repositories.
