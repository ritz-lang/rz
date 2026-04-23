# ritz1 - The Ritz Self-Hosting Compiler

The Ritz compiler written in Ritz, compiled by ritz0, growing incrementally
towards full self-hosting.

## Status

11 source modules, ~13,700 lines of Ritz. Compiled by ritz0 into a native
Linux binary that can compile Ritz programs to LLVM IR.

**Current capabilities:**
- Full lexer with NFA-based tokenization and indentation tracking
- Recursive descent parser (generated from grammar)
- Monomorphization of generic functions and structs
- LLVM IR code generation with SSA form
- Recursive import resolution via `RITZ_PATH`
- Separate compilation (1 `.ritz` file -> 1 `.ll` file)

## Build

```bash
# Build ritz1 using ritz0
make ritz1

# Or manually:
cd projects/ritz/ritz1
python ../ritz0/ritz0.py src/main.ritz --no-runtime -o build/main.ll
# ... repeat for all 11 modules, then link
```

## Usage

```bash
./build/ritz1 <input.ritz> -o <output.ll>
./build/ritz1 <input.ritz> -o <output.ll> -I <ritz_path>
```

## Bootstrap

ritz1 can compile itself:

```bash
make bootstrap   # builds ritz1_selfhosted using ritz1
make verify      # tests both binaries produce correct output
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed module documentation,
dependency graph, and compilation pipeline.

## Directory Structure

```
ritz1/
├── src/                     # Compiler source (11 .ritz + 11 .sig files)
│   ├── tokens_gen.ritz      # Token type constants (generated)
│   ├── nfa.ritz             # NFA engine
│   ├── regex.ritz           # Regex -> NFA compiler
│   ├── lexer_nfa.ritz       # NFA-based lexer
│   ├── lexer_setup_gen.ritz # Lexer pattern setup (generated)
│   ├── ast.ritz             # AST node types
│   ├── ast_helpers.ritz     # AST construction helpers
│   ├── parser_gen.ritz      # Recursive descent parser (generated)
│   ├── monomorph.ritz       # Generic monomorphization
│   ├── emitter.ritz         # LLVM IR code generator
│   └── main.ritz            # Compiler driver
├── test/                    # Test programs
├── runtime/                 # Minimal runtime support
├── bootstrap_ritzlib/       # Bootstrap ritzlib stubs
├── Makefile                 # Build system
├── compile.sh               # Alternative build script
├── ARCHITECTURE.md          # Module-level documentation
└── README.md                # This file
```

## See Also

- **ritz0/** - Python bootstrap compiler
- **ritzlib/** - Standard library modules
- **examples/** - Example programs
