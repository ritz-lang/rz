# RFC: Multi-line Import Statements

**Status:** Proposed
**Author:** Tome (Adele)
**Date:** 2026-02-13

---

## Executive Summary

This RFC proposes supporting multi-line import statements with selective imports that span multiple lines, improving readability for modules with many exports.

---

## 1. Problem Statement

### Current Behavior

Currently, import statements with selective imports must be on a single line:

```ritz
import lib.store { Store, store_new, store_get, store_create }
```

When importing many symbols, this becomes unwieldy:

```ritz
# This fails with "Expected item name" at the line break
import lib.store { Store, store_new, store_get, store_create, store_update_title,
                   store_update_content, store_update_status, store_move, store_delete,
                   store_children_count, store_get_child, store_add_link }
```

### Impact

| Problem | Effect |
|---------|--------|
| **Long lines** | Lines exceed reasonable width (80-120 chars) |
| **Reduced readability** | Hard to scan which symbols are imported |
| **Workaround tax** | Must use full module import and qualify all calls |

### Current Workaround

Import the entire module and prefix all calls:

```ritz
import lib.store

# Every call requires qualification
var s: Store = store_new()          # Still works - Store is a type
store_update_title(&s, &id, &title) # Works - function in scope
```

This works but loses the explicitness of selective imports.

---

## 2. Proposed Solution

### 2.1 Allow Line Continuation in Selective Imports

Support multi-line selective imports within `{ }`:

```ritz
import lib.store {
    Store,
    store_new,
    store_get,
    store_create,
    store_update_title,
    store_update_content,
    store_update_status,
}
```

### 2.2 Grammar Changes

Current grammar (informal):
```
import_stmt := 'import' module_path ('{' name_list '}')?
name_list := NAME (',' NAME)*
```

Proposed grammar:
```
import_stmt := 'import' module_path ('{' NEWLINE* name_list NEWLINE* '}')?
name_list := NAME (NEWLINE* ',' NEWLINE* NAME)* ','?
```

Key changes:
- Allow NEWLINE tokens between `{` and first name
- Allow NEWLINE tokens around commas
- Allow optional trailing comma (common in multi-line lists)

### 2.3 Alternative: Backslash Continuation

Some languages use explicit line continuation:

```ritz
import lib.store { Store, store_new, store_get, \
                   store_create, store_update_title }
```

**Not recommended** - adds visual noise and is error-prone.

---

## 3. Implementation

### Parser Changes (ritz0/parser.py)

In `parse_import()`:

```python
def parse_import(self):
    self.expect(TokenKind.IMPORT)
    module_path = self.parse_module_path()

    imports = []
    if self.match(TokenKind.LBRACE):
        self.skip_newlines()  # NEW: Allow newlines after {
        while not self.check(TokenKind.RBRACE):
            imports.append(self.expect(TokenKind.NAME))
            self.skip_newlines()  # NEW: Allow newlines around comma
            if not self.match(TokenKind.COMMA):
                break
            self.skip_newlines()  # NEW: Allow newlines after comma
        self.expect(TokenKind.RBRACE)

    return ImportNode(module_path, imports)
```

### Lexer Changes

None required - NEWLINE is already a token.

---

## 4. Examples

### Before
```ritz
# Option 1: Single long line (hard to read)
import lib.store { Store, store_new, store_get, store_create, store_update_title, store_update_content }

# Option 2: Full module import (loses explicitness)
import lib.store
```

### After
```ritz
# Clear, readable multi-line import
import lib.store {
    Store,
    store_new,
    store_get,
    store_create,
    store_update_title,
    store_update_content,
}
```

---

## 5. Compatibility

- **Backward compatible** - All existing single-line imports continue to work
- **No semantic changes** - Only parser/syntax change

---

## 6. Alternatives Considered

| Alternative | Reason Rejected |
|------------|-----------------|
| Backslash continuation | Noisy, error-prone |
| Multiple import statements | Verbose, repetitive |
| Import aliases only | Doesn't solve the core problem |

---

## 7. References

- Rust: `use module::{A, B, C};` supports multi-line
- Python: `from module import (A, B, C)` supports multi-line with parens
- Go: `import ("a"; "b")` groups imports
