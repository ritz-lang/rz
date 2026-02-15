# ritzgen-py

Python parser generator that reads `grammars/ritz.grammar` and generates a Python-based recursive descent parser.

## Purpose

Replace hand-written `ritz0/parser.py` with generated code from the canonical grammar. This ensures:

1. **Single source of truth**: `grammars/ritz.grammar` defines the language
2. **No drift**: Parser exactly matches grammar specification
3. **Reusable**: Same grammar can generate ritz1 (self-hosted) parser

## Usage

```bash
# Generate parser from grammar
python3 -m tools.ritzgen_py.generator grammars/ritz.grammar > ritz0/parser_gen.py

# Generate with verbose output
python3 -m tools.ritzgen_py.generator grammars/ritz.grammar --verbose
```

## Architecture

```
tools/ritzgen_py/
├── __init__.py
├── grammar_parser.py   # Parse .grammar files
├── generator.py        # Generate Python parser code
└── README.md
```

## Grammar Format

The grammar file uses a BNF-like syntax:

```
%tokens
KEYWORD = "literal"      # Exact string match
IDENT = /[a-zA-Z_]+/     # Regex pattern

%skip
WHITESPACE = /[ \t]+/    # Patterns to ignore

%grammar
rule -> ReturnType
    : alternative1 { action }
    | alternative2 { action }
    ;
```

## Generated Code

The generator produces:
- Token constants (TOK_*)
- Lexer class with tokenize()
- Parser class with parse_* methods for each rule
- AST node classes

The generated parser integrates with existing `emitter_llvmlite.py`.
