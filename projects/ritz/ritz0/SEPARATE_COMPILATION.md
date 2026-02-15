# Separate Compilation for ritz0

## Status: IMPLEMENTED

Separate compilation is now working. This enables compiling each `.ritz` module to its own `.o` file and linking them together.

## Usage

### Compile with --separate flag

```bash
# Compile a library module (no _start, declares for imported symbols)
python3 ritz0/ritz0.py ritzlib/sys.ritz --separate --no-runtime -o sys.ll
llc -O2 -filetype=obj sys.ll -o sys.o

# Compile main module (has _start, defines for local, declares for imported)
python3 ritz0/ritz0.py examples/11_grep/src/main.ritz --separate -o grep.ll
llc -O2 -filetype=obj grep.ll -o grep.o

# Link all object files
ld -dynamic-linker /lib64/ld-linux-x86-64.so.2 -lc -o grep \
  sys.o io.o str.o args.o grep.o
```

### Behavior

With `--separate`:
- Functions from the main source file: emitted with `define` (full body)
- Functions from imported modules: emitted with `declare` only (external reference)
- Struct types: fully defined in all modules (required by LLVM)
- Constants: inlined at compile time
- Extern functions: declared in all modules that use them

## Implementation Details

### 1. Source File Tracking (ritz_ast.py)

The `Item` base class now supports a `source_file` attribute. This is set dynamically (not as a dataclass field to avoid inheritance issues):

```python
class Item(Node):
    """Base class for top-level items.

    Items track their source file for separate compilation.
    Set via: item.source_file = path
    """
    pass
```

### 2. Import Resolver (import_resolver.py)

When registering items, the resolver sets the source file path:

```python
def _register_item(self, item: rast.Item, source_file: str):
    item.source_file = source_file
    # ... rest of registration
```

### 3. Monomorphization (monomorph.py)

The monomorph pass preserves `source_file` when creating new FnDef objects:

```python
new_fn = rast.FnDef(...)
if hasattr(fn, 'source_file'):
    new_fn.source_file = fn.source_file
return new_fn
```

### 4. Emitter (emitter_llvmlite.py)

The emitter checks `source_file` to decide whether to emit a function body:

```python
def _should_emit_body(self, item: rast.Item) -> bool:
    if self._current_source_file is None:
        return True  # Legacy behavior
    item_source = getattr(item, 'source_file', None)
    if item_source is None:
        return True
    return item_source == self._current_source_file
```

Functions without bodies become declarations:
```llvm
; Imported function - declaration only
declare i64 @"sys_read"(i32 %".1", i8* %".2", i64 %".3")

; Local function - full definition
define i32 @"main"(i32 %"argc.arg", i8** %"argv.arg") {
  ; ... body ...
}
```

### 5. CLI (ritz0.py)

New `--separate` flag enables separate compilation:

```python
parser.add_argument('--separate', action='store_true',
                   help='Separate compilation: only emit function bodies from main source')
```

## Verified Working

Tested with `examples/11_grep`:

```
=== Compilation Sizes ===
Normal (monolithic):   4491 lines LLVM IR → 25544 byte binary
Separate (main only):   772 lines LLVM IR → 25672 byte binary (linked from 5 .o files)

=== grep example works correctly ===
$ /tmp/grep_linked world /tmp/test.txt
Hello world
Goodbye world
```

## Benefits

1. **Incremental compilation**: Only recompile changed modules
2. **Smaller compilation units**: Faster individual compiles
3. **Linking flexibility**: Can link Ritz code with external object files
4. **No duplicate definitions**: Each function defined exactly once

## Limitations

1. **Struct types duplicated**: LLVM requires struct definitions in each module
2. **Constants inlined**: Not shared as symbols (minor inefficiency)
3. **Generic functions**: Specialized versions are duplicated per module that uses them
4. **No automatic dependency tracking**: Manual compilation order required (for now)

## Future Work

1. Build system integration with automatic dependency tracking
2. Cache `.ll` and `.o` files in `.ritz-cache/`
3. Parallel compilation of independent modules
4. Header/interface file generation for faster imports
