# Ritz Packaging

## Project Structure

```
myproject/
  ritz.toml          # package manifest
  src/
    main.ritz        # entry point (executables)
    lib.ritz         # entry point (libraries)
    utils.ritz       # other modules
  test/
    test_utils.ritz  # tests
  deps/              # vendored dependencies
  target/            # build output
```

## Manifest: ritz.toml

```toml
[package]
name = "myproject"
version = "0.1.0"
authors = ["Your Name <you@example.com>"]

[deps]
ritzlib = { git = "https://github.com/ritz-lang/ritzlib", tag = "v0.1" }
json = { path = "../json" }

[build]
target = "x86_64-linux"

[test]
runner = "jit"       # "jit" (fast) or "aot" (optimized)
```

## Module Resolution

```ritz
# From dependencies
import ritzlib.fs           # deps/ritzlib/src/fs.ritz
import ritzlib.io.File      # deps/ritzlib/src/io.ritz, type File

# From same package
import utils                # src/utils.ritz
import utils.parse_int      # specific function
```

## Build Output

```
target/
  debug/
    myproject           # debug executable
    myproject.ll        # LLVM IR (if --emit ll)
  release/
    myproject           # optimized executable
```

## Commands

```bash
# In project root
ritz build              # build src/main.ritz or src/lib.ritz
ritz test               # run tests from test/
ritz run                # build and execute

# Specify output
ritz build -o bin/myapp
```

## Library vs Executable

- If `src/main.ritz` exists → executable, entry point is `fn main()`
- If `src/lib.ritz` exists → library, exports public symbols
- Both can exist (library with example binary)
