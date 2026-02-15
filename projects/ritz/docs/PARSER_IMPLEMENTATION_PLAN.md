# Parser Implementation Plan

## Goal

Transform the monolithic 3,569-line `parser.ritz` into modular sub-500-line files while preserving the grammar-driven generation approach.

---

## Step 1: Enhance the Generator

### 1.1 Define Module Boundaries in Grammar

Add annotations to the grammar to indicate module boundaries:

```grammar
# @module toplevel
module -> *Module
    : module_init item* { p.module }
    ;

fn_def -> *FnDef
    : FN IDENT generic_params? LPAREN params? RPAREN return_type? block
      { generic_fn_def_new(p, ...) }
    ;

# @module stmt
stmt -> *Stmt
    : let_stmt
    | var_stmt
    | ...
    ;

# @module expr
expr -> *Expr
    : or_expr
    ;
```

The generator reads these annotations and groups rules into output files.

### 1.2 Alternative: Automatic Module Detection

Alternatively, the generator can use heuristics:
- Rules starting with `module`, `fn_def`, `struct_def`, `impl_block` → `parser_toplevel.ritz`
- Rules containing `stmt` → `parser_stmt.ritz`
- Rules containing `expr`, `binary`, `unary`, `postfix` → `parser_expr.ritz`
- Rules containing `type_spec`, `generic_params` → `parser_type.ritz`

### 1.3 Generate Import Graph

When splitting, the generator must:
1. Track which rules call which other rules
2. Generate appropriate import statements
3. Make public only what's needed across module boundaries

Example:
```ritz
# parser_stmt.ritz
import ast
import ast_helpers
import tokens
import parser_expr    # for parse_expr()
import parser_type    # for parse_type_spec()

fn parse_let_stmt(p: *Parser) -> *Stmt
    ...
```

---

## Step 2: Implement Split Generator

### 2.1 New Generator Structure

```python
# ritz_generator.py additions

class ModuleSplitter:
    """Split grammar rules into modules."""

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.modules = {
            'core': [],      # p_peek, p_advance, parser_init
            'toplevel': [],  # module, fn_def, struct_def, impl
            'stmt': [],      # stmt, let_stmt, if_stmt, etc.
            'expr': [],      # expr, binary ops, unary, postfix
            'type': [],      # type_spec, generic_params
        }

    def categorize_rule(self, rule: GrammarRule) -> str:
        """Determine which module a rule belongs to."""
        name = rule.name

        if name in ('module', 'module_init', 'item', 'fn_def', 'extern_fn_def',
                    'struct_def', 'const_def', 'import_stmt', 'global_var_def',
                    'impl_block', 'impl_methods'):
            return 'toplevel'

        if 'stmt' in name or name in ('block', 'stmts'):
            return 'stmt'

        if any(x in name for x in ('expr', 'binary', 'unary', 'postfix',
                                    'primary', 'args', 'cast', 'addr')):
            return 'expr'

        if 'type' in name or name in ('generic_params', 'type_param_list'):
            return 'type'

        # Default: check what it returns
        if rule.return_type and 'Stmt' in rule.return_type:
            return 'stmt'
        if rule.return_type and 'Expr' in rule.return_type:
            return 'expr'

        return 'toplevel'  # default

    def split(self) -> Dict[str, List[GrammarRule]]:
        for rule in self.grammar.rules:
            module = self.categorize_rule(rule)
            self.modules[module].append(rule)
        return self.modules
```

### 2.2 Generate Per-Module Files

```python
def generate_split_parser(self) -> Dict[str, str]:
    """Generate multiple parser files."""
    splitter = ModuleSplitter(self.grammar)
    modules = splitter.split()

    results = {}

    # Generate core
    results['parser_core.ritz'] = self._generate_core_module()

    # Generate each module
    for name, rules in modules.items():
        if name == 'core':
            continue
        content = self._generate_parser_module(name, rules, modules)
        results[f'parser_{name}.ritz'] = content

    return results
```

### 2.3 Track Dependencies

```python
def _compute_dependencies(self, rules: List[GrammarRule],
                          all_modules: Dict[str, List[GrammarRule]]) -> Set[str]:
    """Compute which modules this set of rules depends on."""
    deps = set()

    rule_to_module = {}
    for mod_name, mod_rules in all_modules.items():
        for r in mod_rules:
            rule_to_module[r.name] = mod_name

    for rule in rules:
        for alt in rule.alternatives:
            for sym in alt.symbols:
                if sym.kind == SymbolKind.NONTERMINAL:
                    if sym.name in rule_to_module:
                        dep_mod = rule_to_module[sym.name]
                        if dep_mod != self._current_module:
                            deps.add(dep_mod)

    return deps
```

---

## Step 3: Split AST Helpers

### 3.1 Create Directory Structure

```bash
mkdir -p ritz1/src/ast_helpers
```

### 3.2 Split by Responsibility

| File | Functions | Lines |
|------|-----------|-------|
| `alloc.ritz` | `parser_alloc` | ~10 |
| `module.ritz` | `module_new`, `module_add_*`, `impl_block_new`, `global_var_new` | ~100 |
| `fn.ritz` | `fn_def_new`, `extern_fn_def_new`, `generic_fn_def_new`, `param_*`, `type_param_*` | ~150 |
| `struct.ritz` | `struct_def_new`, `field_new`, `generic_struct_def_new`, `field_link` | ~100 |
| `stmt.ritz` | All `stmt_*` functions | ~200 |
| `expr.ritz` | `expr_int`, `expr_string`, `expr_ident`, `expr_binary`, etc. | ~200 |
| `postfix.ritz` | `postfix_*`, `apply_postfix_p`, `binary_op_new`, `apply_binary_opt_p` | ~150 |
| `type.ritz` | `type_named`, `type_ptr`, `type_array`, `type_ref`, `type_generic`, `capture_fn_return_type` | ~100 |
| `literal.ritz` | `field_init_*`, `ident_or_struct`, `generic_struct_lit` | ~100 |
| `parse.ritz` | `parse_int`, `parse_hex`, `parse_binary` | ~50 |

### 3.3 Create Index File

```ritz
# ast_helpers/mod.ritz
import ast_helpers.alloc
import ast_helpers.module
import ast_helpers.fn
import ast_helpers.struct
import ast_helpers.stmt
import ast_helpers.expr
import ast_helpers.postfix
import ast_helpers.type
import ast_helpers.literal
import ast_helpers.parse

# Re-export all public functions
pub use ast_helpers.alloc.*
pub use ast_helpers.module.*
# etc.
```

**Note:** If Ritz doesn't support `mod.ritz` or `pub use`, we keep the flat import model but split the source files. The parser files import what they need directly.

---

## Step 4: Update Build System

### 4.1 Update ritz.toml

```toml
[package]
name = "ritz1"
version = "0.1.0"
sources = ["src", "src/ast_helpers"]  # Add subdirectory
```

### 4.2 Update Generator Makefile/Script

```bash
#!/bin/bash
# generate_parser.sh

GRAMMAR=grammars/ritz1.grammar
OUTPUT_DIR=ritz1/src

# Generate split parser files
python3 tools/ritzgen_py/ritz_generator.py $GRAMMAR \
    --output-dir $OUTPUT_DIR \
    --split

echo "Generated:"
ls -la $OUTPUT_DIR/parser_*.ritz
```

---

## Step 5: Validation

### 5.1 Rebuild and Test

```bash
# Clean build
cd ritz1-bootstrap
./ritz0 compile ritz1 --no-cache

# Run examples
./test_examples.sh
```

### 5.2 Verify Line Counts

```bash
wc -l ritz1/src/parser_*.ritz
# Each should be <500 lines

wc -l ritz1/src/ast_helpers/*.ritz
# Each should be <300 lines
```

### 5.3 Check Imports Work

Ensure cross-module function calls work:
- `parser_stmt.ritz` calling `parse_expr()` from `parser_expr.ritz`
- `parser_expr.ritz` calling `parse_type_spec()` from `parser_type.ritz`

---

## Timeline

| Phase | Time Estimate | Deliverables |
|-------|---------------|--------------|
| 1. Generator changes | 2 hours | Split file generation |
| 2. AST helpers split | 1 hour | Modular ast_helpers/ |
| 3. Integration | 1 hour | Working builds |
| 4. Testing | 1 hour | All examples pass |
| **Total** | **5 hours** | Modular parser system |

---

## Rollback Plan

If the split causes issues:
1. Keep original `ritz_generator.py` as `ritz_generator_v1.py`
2. Add `--no-split` flag to revert to monolithic output
3. Original `ast_helpers.ritz` is backed up

---

## Success Criteria

1. ✅ No file exceeds 500 lines (800 max for complex modules)
2. ✅ `wc -l parser.ritz` → file doesn't exist (split into modules)
3. ✅ All 83 examples compile (at least as many as before)
4. ✅ Build time unchanged or faster
5. ✅ Zero hand-edits to generated parser files
