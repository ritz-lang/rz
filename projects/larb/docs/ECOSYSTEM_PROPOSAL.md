# RFC: Flat Ecosystem and Import Resolution

**LARB Proposal** | **Status:** Draft | **Date:** 2026-02-14

This document proposes the import resolution system for the Ritz ecosystem, enabling a flat sibling structure where all projects can reference each other without nested submodule hell.

---

## 1. Problem Statement

### The Submodule Nightmare

Traditional dependency management via git submodules creates deeply nested structures:

```
your-app/
├── ritz/                    # Your copy
├── squeeze/
│   └── ritz/                # Squeeze's copy (duplicate!)
├── valet/
│   ├── ritz/                # Valet's copy (duplicate!)
│   └── squeeze/
│       └── ritz/            # Triple nested!
```

**Problems:**
- Multiple copies of the same dependency
- Version conflicts between nested copies
- Changes to `ritz` require updating every nested copy
- Contributing upstream is a nightmare of rebasing

### Current State

The ecosystem projects (ritz, squeeze, valet, etc.) exist as siblings under `ritz-lang/` but:
- No formal import resolution mechanism
- No documented workflow for contributing upstream
- The compiler doesn't know how to find sibling packages

---

## 2. Proposed Solution: RITZ_PATH

### 2.1 Environment Variable

```bash
export RITZ_PATH=~/dev/ritz-lang
```

`RITZ_PATH` points to the directory containing all Ritz ecosystem projects as **flat siblings**:

```
$RITZ_PATH/
├── ritz/           # Compiler + ritzlib
├── ritzunit/       # Test framework
├── squeeze/        # Compression
├── cryptosec/      # Cryptography
├── valet/          # HTTP server
├── zeus/           # App server
├── mausoleum/      # Document database
├── tome/           # Cache
├── spire/          # Web framework
├── harland/        # Kernel
├── larb/           # Standards
└── my-app/         # Your application
```

### 2.2 Import Resolution Algorithm

When the compiler encounters `import foo.bar`:

```
1. Check project-local paths first:
   - ./src/foo/bar.ritz
   - ./src/foo.ritz (for module foo containing bar)

2. Check RITZ_PATH sibling packages:
   - $RITZ_PATH/foo/src/bar.ritz
   - $RITZ_PATH/foo/src/bar/mod.ritz

3. Check ritzlib (special case for standard library):
   - $RITZ_PATH/ritz/ritzlib/foo.ritz (for ritzlib.foo)
```

### 2.3 Import Syntax

```ritz
# Standard library (from ritz/ritzlib/)
import ritzlib.sys
import ritzlib.gvec { Vec }

# Ecosystem packages (from $RITZ_PATH/<package>/src/)
import squeeze.gzip
import cryptosec.sha256 { SHA256 }
import valet.http { Request, Response }

# Project-local imports
import mymodule           # ./src/mymodule.ritz or ./src/mymodule/mod.ritz
import mymodule.submod    # ./src/mymodule/submod.ritz
```

### 2.4 Package Manifest (ritz.toml)

Each project declares its identity and dependencies:

```toml
[package]
name = "valet"
version = "0.5.0"

# Source roots (relative to project root)
sources = ["src"]

# Binary targets
[[bin]]
name = "valet"
entry = "main::main"

# Dependencies reference sibling packages
[dependencies]
ritzlib = { path = "../ritz/ritzlib" }   # Standard library
squeeze = { path = "../squeeze" }         # Compression
cryptosec = { path = "../cryptosec" }     # Crypto
```

**Note:** Paths are relative to the project root, but with `RITZ_PATH` set, the compiler can resolve `squeeze` directly without explicit path configuration.

---

## 3. Submodules for Contribution

### 3.1 The Contribution Workflow

When you need to modify a dependency (e.g., fix a bug in `squeeze` while working on `valet`):

**Option A: Edit the sibling directly** (preferred for ecosystem developers)
```bash
# You're working on valet and find a bug in squeeze
cd $RITZ_PATH/squeeze
git checkout -b fix/my-bugfix

# Fix the bug with TDD
# ... edit, test ...

git commit -m "squeeze: Fix edge case in deflate"
git push -u origin fix/my-bugfix
gh pr create

# Continue working on valet - it already sees your fix
cd $RITZ_PATH/valet
```

**Option B: Local submodule override** (for isolated changes)
```bash
cd $RITZ_PATH/valet

# Add squeeze as a submodule for your branch
git submodule add -b fix/my-bugfix ../squeeze deps/squeeze

# Configure the compiler to use the submodule first
# (see Section 4: Override Resolution)
```

### 3.2 Submodule Takes Precedence

When a submodule exists in a project's `deps/` directory, it **takes precedence** over the `RITZ_PATH` sibling:

```
Resolution order:
1. ./deps/<package>/src/     # Submodule override (highest priority)
2. ./src/                    # Project-local
3. $RITZ_PATH/<package>/src/ # Sibling package (fallback)
```

This enables:
- Working on a fix in isolation
- Testing your changes before they're merged upstream
- Submitting PRs while using the fixed version

### 3.3 Lifecycle

```
1. DISCOVER  - Find bug in dependency while working on your project
2. BRANCH    - Create fix branch in the dependency ($RITZ_PATH/<dep>)
3. FIX       - Implement with TDD, commit
4. SUBMIT    - Push branch, create PR
5. CONTINUE  - Your project already uses the fix (sibling is modified)
6. MERGE     - PR accepted, switch dependency back to main
7. CLEANUP   - If you used submodule override, remove it
```

---

## 4. Override Resolution

### 4.1 deps/ Directory Structure

Projects can override dependencies using local submodules:

```
valet/
├── deps/                    # Dependency overrides
│   └── squeeze/             # Submodule: git@github.com:you/squeeze.git#fix/my-bug
│       └── src/
├── src/
│   └── main.ritz
└── ritz.toml
```

### 4.2 Resolution Priority

```
Priority (highest to lowest):
1. deps/<package>/src/          # Local submodule override
2. src/                         # Project-local source
3. $RITZ_PATH/<package>/src/    # Sibling package
4. $RITZ_PATH/ritz/ritzlib/     # Standard library
```

### 4.3 Compiler Flags

```bash
# Use specific package path (overrides RITZ_PATH lookup)
ritz build --package-path squeeze=./deps/squeeze

# Ignore deps/ overrides (use RITZ_PATH only)
ritz build --no-local-deps

# Print resolution order for debugging
ritz build --verbose-imports
```

---

## 5. Compiler Implementation

### 5.1 Required Changes

The compiler needs to:

1. **Read RITZ_PATH** from environment
2. **Parse ritz.toml** in each package
3. **Implement resolution algorithm** (Section 2.2)
4. **Support deps/ overrides** (Section 4.1)
5. **Cache parsed imports** across packages

### 5.2 Import Resolution Pseudocode

```python
def resolve_import(import_path: str, current_package: Package) -> Path:
    parts = import_path.split('.')
    package_name = parts[0]
    module_path = '/'.join(parts[1:]) + '.ritz'

    # 1. Check deps/ override
    deps_path = current_package.root / 'deps' / package_name / 'src' / module_path
    if deps_path.exists():
        return deps_path

    # 2. Check project-local (if package_name matches current)
    if package_name == current_package.name:
        local_path = current_package.root / 'src' / module_path
        if local_path.exists():
            return local_path

    # 3. Check RITZ_PATH siblings
    ritz_path = os.environ.get('RITZ_PATH')
    if ritz_path:
        # Special case: ritzlib
        if package_name == 'ritzlib':
            stdlib_path = Path(ritz_path) / 'ritz' / 'ritzlib' / module_path
            if stdlib_path.exists():
                return stdlib_path

        # Regular package
        sibling_path = Path(ritz_path) / package_name / 'src' / module_path
        if sibling_path.exists():
            return sibling_path

    raise ImportError(f"Cannot resolve import: {import_path}")
```

### 5.3 Error Messages

```
error: cannot resolve import 'squeeze.gzip'
  --> src/main.ritz:3:1
   |
 3 | import squeeze.gzip
   | ^^^^^^^^^^^^^^^^^^^
   |
   = help: RITZ_PATH is set to '/home/user/dev/ritz-lang'
   = help: expected to find '/home/user/dev/ritz-lang/squeeze/src/gzip.ritz'
   = help: run `ls $RITZ_PATH` to see available packages
```

---

## 6. Benefits

### 6.1 For Ecosystem Developers

- **Single source of truth** - One copy of each package
- **Instant propagation** - Changes visible immediately across all projects
- **Easy contribution** - Branch, fix, PR, continue
- **No sync headaches** - No nested submodule updates

### 6.2 For Application Developers

- **Simple setup** - Clone repos, set RITZ_PATH, done
- **Override flexibility** - Pin specific versions via submodules when needed
- **Clear resolution** - `--verbose-imports` shows exactly what's being used

### 6.3 For the Compiler

- **Deterministic** - Same RITZ_PATH = same resolution
- **Cacheable** - Package paths are stable
- **Debuggable** - Clear error messages with resolution hints

---

## 7. Migration Path

### 7.1 From Nested Submodules

```bash
# 1. Remove nested submodules
git submodule deinit --all -f
rm -rf .git/modules/* projects/

# 2. Set up flat structure
export RITZ_PATH=~/dev/ritz-lang
cd $RITZ_PATH
git clone git@github.com:ritz-lang/ritz.git
git clone git@github.com:ritz-lang/squeeze.git
# ... clone all needed projects ...

# 3. Verify imports work
cd $RITZ_PATH/valet
ritz build --verbose-imports
```

### 7.2 LARB Repository

LARB itself no longer needs submodules. It's a standards/documentation repository that references sibling projects by documentation, not by embedding them.

```
$RITZ_PATH/
├── larb/                    # Standards (this repo)
│   ├── docs/                # Specifications
│   ├── tools/               # ritz-lint, etc.
│   └── archive/             # Historical documents
├── ritz/                    # Compiler (sibling, not submodule)
├── squeeze/                 # Compression (sibling)
└── ...
```

---

## 8. Open Questions

### 8.1 Version Pinning

Should `ritz.toml` support version constraints?

```toml
[dependencies]
squeeze = { version = ">=0.5.0" }  # Check version in squeeze's ritz.toml?
```

**Current stance:** No. The flat model assumes you're working with HEAD of all siblings. Version pinning is for published packages (future package registry).

### 8.2 Remote Dependencies

Should the compiler fetch remote packages?

```toml
[dependencies]
some-lib = { git = "https://github.com/user/some-lib.git" }
```

**Current stance:** No. Clone it to RITZ_PATH yourself. Keeps the compiler simple.

### 8.3 Multiple RITZ_PATHs

Should we support searching multiple paths?

```bash
export RITZ_PATH=~/dev/ritz-lang:~/dev/my-ritz-libs
```

**Current stance:** Maybe. Unix PATH semantics are familiar. But keep it simple for v1.

---

## 9. Implementation Checklist

### Phase 1: Basic Resolution
- [ ] Implement RITZ_PATH environment variable reading
- [ ] Implement basic import resolution (Section 2.2)
- [ ] Add `--verbose-imports` flag
- [ ] Update error messages with resolution hints

### Phase 2: deps/ Overrides
- [ ] Implement deps/ directory scanning
- [ ] Add `--package-path` flag for manual overrides
- [ ] Add `--no-local-deps` flag

### Phase 3: Documentation
- [ ] Update AGENT.md with finalized semantics
- [ ] Update all project READMEs with setup instructions
- [ ] Create "Contributing to Dependencies" guide

---

## 10. Summary

The flat ecosystem model with RITZ_PATH provides:

1. **Simplicity** - All projects as siblings, one environment variable
2. **Flexibility** - Override with deps/ submodules when needed
3. **Contribution-friendly** - Branch sibling, fix, PR, continue
4. **No nesting** - Avoid the submodule dependency hell

This enables the "No Concessions" workflow: when you find a bug in a dependency, you fix it upstream immediately, your project uses the fix instantly, and you submit a PR without disrupting your workflow.
