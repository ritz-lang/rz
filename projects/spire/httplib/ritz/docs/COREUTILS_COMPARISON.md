# Ritz Examples vs Coreutils Comparison

This document compares our Ritz implementations against GNU coreutils to identify feature gaps and improvement opportunities.

---

## Summary

| Tier | Examples | Status | Key Gaps |
|------|----------|--------|----------|
| 1 (01-10) | Core utilities | ✅ Complete | Limited options |
| 2 (11-20) | Text processing | ✅ Complete | No regex support |
| 3 (21-30) | Filesystem | ✅ Complete | No ACL/xattr support |

---

## Tier 1: Core Utilities (01-10)

### 01_hello
Custom example, not a coreutils equivalent.

### 02_exitcode
Custom example, demonstrates exit codes.

### 03_echo
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Basic output | ✅ | ✅ | - |
| `-n` (no newline) | ✅ | ❌ | Missing |
| `-e` (escapes) | ✅ | ❌ | Missing |
| `-E` (no escapes) | ✅ | ❌ | Missing |

### 04_true_false
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| `true` returns 0 | ✅ | ✅ | - |
| `false` returns 1 | ✅ | ✅ | - |

### 05_cat
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Concatenate files | ✅ | ✅ | - |
| Read stdin | ✅ | ✅ | - |
| `-n` (line numbers) | ✅ | ❌ | Missing |
| `-b` (non-blank numbers) | ✅ | ❌ | Missing |
| `-s` (squeeze blanks) | ✅ | ❌ | Missing |
| `-E` (show ends) | ✅ | ❌ | Missing |

### 06_head
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| First N lines | ✅ | ✅ | - |
| `-n NUM` | ✅ | ✅ | - |
| `-c BYTES` | ✅ | ❌ | Missing |
| Multiple files | ✅ | ❌ | Missing headers |

### 07_wc
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Line count | ✅ | ✅ | - |
| Word count | ✅ | ✅ | - |
| Byte count | ✅ | ✅ | - |
| `-l/-w/-c` flags | ✅ | ✅ | - |
| Multiple files | ✅ | ✅ | - |
| Total line | ✅ | ❌ | Missing |

### 08_seq
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Count to N | ✅ | ✅ | - |
| Start/end range | ✅ | ✅ | - |
| Step value | ✅ | ✅ | - |
| `-s SEPARATOR` | ✅ | ❌ | Missing |
| `-w` (equal width) | ✅ | ❌ | Missing |
| Float support | ✅ | ❌ | Missing |

### 09_yes
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Repeat "y" | ✅ | ✅ | - |
| Custom string | ✅ | ✅ | - |

### 10_sleep
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Sleep N seconds | ✅ | ✅ | - |
| Float seconds | ✅ | ❌ | Missing |
| Suffix (m/h/d) | ✅ | ❌ | Missing |

---

## Tier 2: Text Processing (11-20)

### 11_grep
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Fixed string search | ✅ | ✅ | - |
| `-i` (case insensitive) | ✅ | ✅ | - |
| `-v` (invert match) | ✅ | ✅ | - |
| `-n` (line numbers) | ✅ | ✅ | - |
| `-c` (count only) | ✅ | ✅ | - |
| Regex patterns | ✅ | ❌ | **Major gap** |
| `-E` (extended regex) | ✅ | ❌ | Missing |
| `-r` (recursive) | ✅ | ❌ | Missing |
| `-l` (files only) | ✅ | ❌ | Missing |

### 12_tac
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Reverse lines | ✅ | ✅ | - |
| `-s SEPARATOR` | ✅ | ❌ | Missing |

### 13_sort
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Alphabetic sort | ✅ | ✅ | - |
| `-r` (reverse) | ✅ | ✅ | - |
| `-n` (numeric) | ✅ | ✅ | - |
| `-u` (unique) | ✅ | ❌ | Missing |
| `-k` (key field) | ✅ | ❌ | Missing |
| `-t` (delimiter) | ✅ | ❌ | Missing |
| Stable sort | ✅ | ❌ | Missing |

### 14_uniq
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Remove adjacent dups | ✅ | ✅ | - |
| `-c` (count) | ✅ | ✅ | - |
| `-d` (only dups) | ✅ | ✅ | - |
| `-u` (only unique) | ✅ | ✅ | - |
| `-i` (case insensitive) | ✅ | ✅ | - |
| `-f` (skip fields) | ✅ | ❌ | Missing |
| `-s` (skip chars) | ✅ | ❌ | Missing |

### 15_cut
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| `-f` (fields) | ✅ | ✅ | - |
| `-d` (delimiter) | ✅ | ✅ | - |
| `-c` (characters) | ✅ | ✅ | - |
| `-b` (bytes) | ✅ | ❌ | Missing |
| `--complement` | ✅ | ❌ | Missing |

### 16_tr
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Character translation | ✅ | ✅ | - |
| `-d` (delete) | ✅ | ✅ | - |
| `-s` (squeeze) | ✅ | ✅ | - |
| `-c` (complement) | ✅ | ✅ | - |
| Character classes | ✅ | ❌ | Missing ([:alpha:] etc) |
| Character ranges | ✅ | ✅ | - |

### 17_expand
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Tab to spaces | ✅ | ✅ | - |
| `-t N` (tab stops) | ✅ | ✅ | - |
| `-i` (initial only) | ✅ | ✅ | - |
| Multiple tab stops | ✅ | ❌ | Missing |

### 18_nl
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Number lines | ✅ | ✅ | - |
| `-b` (body numbering) | ✅ | ✅ | - |
| `-w` (width) | ✅ | ✅ | - |
| `-s` (separator) | ✅ | ✅ | - |
| `-n` (format) | ✅ | ✅ | - |
| Section support | ✅ | ❌ | Missing |

### 19_base64
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Encode | ✅ | ✅ | - |
| `-d` (decode) | ✅ | ✅ | - |
| `-w` (wrap) | ✅ | ✅ | - |
| `-i` (ignore garbage) | ✅ | ❌ | Missing |

### 20_xxd
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Hex dump | ✅ | ✅ | - |
| `-r` (reverse) | ✅ | ✅ | - |
| `-c` (columns) | ✅ | ✅ | - |
| `-g` (grouping) | ✅ | ✅ | - |
| `-p` (plain) | ✅ | ✅ | - |
| `-u` (uppercase) | ✅ | ✅ | - |
| `-s` (seek) | ✅ | ❌ | Missing |
| `-l` (length) | ✅ | ❌ | Missing |

---

## Tier 3: Filesystem (21-30)

### 21_ls
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| List directory | ✅ | ✅ | - |
| `-l` (long) | ✅ | ✅ | - |
| `-a` (all) | ✅ | ✅ | - |
| `-h` (human sizes) | ✅ | ✅ | - |
| `-F` (classify) | ✅ | ✅ | - |
| `-d` (directory) | ✅ | ✅ | - |
| `-1` (one per line) | ✅ | ✅ | - |
| `-R` (recursive) | ✅ | ❌ | Missing |
| `-t` (time sort) | ✅ | ❌ | Missing |
| `-S` (size sort) | ✅ | ❌ | Missing |
| Color output | ✅ | ❌ | Missing |
| User/group names | ✅ | ❌ | Shows UIDs |

### 22_mkdir
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Create directory | ✅ | ✅ | - |
| `-p` (parents) | ✅ | ✅ | - |
| `-m` (mode) | ✅ | ✅ | - |
| `-v` (verbose) | ✅ | ✅ | - |

### 23_rm
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Remove files | ✅ | ✅ | - |
| `-r` (recursive) | ✅ | ✅ | - |
| `-f` (force) | ✅ | ✅ | - |
| `-v` (verbose) | ✅ | ✅ | - |
| `-i` (interactive) | ✅ | ❌ | Missing |
| `--preserve-root` | ✅ | ❌ | Missing |

### 24_cp
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Copy files | ✅ | ✅ | - |
| `-r` (recursive) | ✅ | ✅ | - |
| `-v` (verbose) | ✅ | ✅ | - |
| `-n` (no clobber) | ✅ | ✅ | - |
| Preserve mode | ✅ | ✅ | - |
| `-p` (preserve all) | ✅ | ❌ | Partial (mode only) |
| `-a` (archive) | ✅ | ❌ | Missing |
| Symlink handling | ✅ | ❌ | Missing |

### 25_mv
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Move/rename | ✅ | ✅ | - |
| `-v` (verbose) | ✅ | ✅ | - |
| `-n` (no clobber) | ✅ | ✅ | - |
| Cross-device move | ✅ | ✅ | - |
| `-i` (interactive) | ✅ | ❌ | Missing |
| `-f` (force) | ✅ | ❌ | Missing |

### 26_touch
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Create file | ✅ | ✅ | - |
| Update timestamps | ✅ | ✅ | - |
| `-a` (access time) | ✅ | ✅ | - |
| `-m` (modify time) | ✅ | ✅ | - |
| `-c` (no create) | ✅ | ✅ | - |
| `-d DATE` | ✅ | ❌ | Missing |
| `-r REF` (reference) | ✅ | ❌ | Missing |

### 27_stat
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Display file status | ✅ | ✅ | - |
| All stat fields | ✅ | ✅ | - |
| `-c FORMAT` | ✅ | ❌ | Missing |
| `-f` (filesystem) | ✅ | ❌ | Missing |

### 28_chmod
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Octal mode | ✅ | ✅ | - |
| Symbolic mode | ✅ | ✅ | - |
| `-R` (recursive) | ✅ | ✅ | - |
| `-v` (verbose) | ✅ | ✅ | - |
| `--reference` | ✅ | ❌ | Missing |

### 29_du
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Disk usage | ✅ | ✅ | - |
| `-s` (summary) | ✅ | ✅ | - |
| `-h` (human) | ✅ | ✅ | - |
| `-a` (all files) | ✅ | ❌ | Missing |
| `-d DEPTH` | ✅ | ❌ | Missing |
| `--exclude` | ✅ | ❌ | Missing |

### 30_find
| Feature | Coreutils | Ritz | Gap |
|---------|-----------|------|-----|
| Find files | ✅ | ✅ | - |
| `-name PATTERN` | ✅ | ✅ | Glob only |
| `-type f/d` | ✅ | ✅ | - |
| `-maxdepth N` | ✅ | ✅ | - |
| `-exec CMD` | ✅ | ❌ | **Major gap** |
| `-mtime` | ✅ | ❌ | Missing |
| `-size` | ✅ | ❌ | Missing |
| Regex support | ✅ | ❌ | Missing |

---

## Key Gaps Summary

### High Priority (Commonly Used)
1. **grep regex** - Most grep usage involves patterns
2. **find -exec** - Essential for automation
3. **ls -R/-t/-S** - Common options
4. **sort -k/-t** - Field-based sorting
5. **echo -n/-e** - Very common options

### Medium Priority
1. **head -c** - Byte limit
2. **cat -n** - Line numbers
3. **wc total** - Multi-file total
4. **cp -a** - Archive mode
5. **tr character classes** - [:alpha:] etc

### Low Priority (Edge Cases)
1. Color output (ls)
2. User/group name resolution
3. Float support (seq, sleep)
4. Section support (nl)
5. ACL/xattr support

---

## Refactoring Plan

### Phase 1: Import Migration
All 30 examples should be updated to use `import ritzlib.*` instead of inline syscall definitions.

**Pattern to replace:**
```ritz
# OLD: Inline syscall
extern fn syscall3(n: i64, a1: i64, a2: i64, a3: i64) -> i64
fn write(fd: i32, buf: *u8, count: i64) -> i64
    return syscall3(1, fd as i64, buf as i64, count)
```

```ritz
# NEW: Import from ritzlib
import ritzlib.sys
import ritzlib.io

# Then use: sys_write(fd, buf, count)
```

### Phase 2: Argument Parsing
Examples with option parsing should use `ritzlib.args`:

**Pattern to replace:**
```ritz
# OLD: Manual arg parsing
var i: i32 = 1
while i < argc
    let arg: *u8 = argv[i]
    if streq(arg, "-v")
        opts.verbose = 1
    # ... etc
```

```ritz
# NEW: Declarative parsing
import ritzlib.args

var parser: ArgParser
args_init(&parser, "prog", "Description")
args_flag(&parser, 'v', "verbose", "Enable verbose")
args_parse(&parser, argc, argv)
```

### Estimated Effort
| Tier | Examples | Avg Lines | Est. Time |
|------|----------|-----------|-----------|
| 1 | 10 | ~70 | 1 hour |
| 2 | 10 | ~320 | 2 hours |
| 3 | 10 | ~340 | 2 hours |
| **Total** | 30 | ~240 | **~5 hours** |

---

## Next Steps

1. ✅ Document current state (this file)
2. ⏳ Create import-based template (21_ls_refactored)
3. ⏳ Batch-refactor examples by tier
4. ⏳ Add missing high-priority features
5. ⏳ Create automated test suite comparing outputs
