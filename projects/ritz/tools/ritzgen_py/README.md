# ritzgen-py

Python parser generator that reads `grammars/ritz1.grammar` and generates the
Ritz sources of ritz1's parser.

## Usage

```bash
python3 tools/ritzgen_py/ritz_generator.py grammars/ritz1.grammar \
    --monolithic --output-dir <dir>
```

`make regen-check` runs this and fails if the committed files in `ritz1/src/`
differ from the output. See `docs/VALIDATION.md`.

## Architecture

```
tools/ritzgen_py/
├── __init__.py
├── grammar_parser.py   # Parse .grammar files
├── ritz_generator.py   # Generate Ritz parser code
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
