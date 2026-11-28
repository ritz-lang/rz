# Packages: source plus a prebuilt archive

**Status:** Approved design (AGAST #4859, epic #4858), landing in slices
(see "Slices"): 1 (identity, #4863), 2 (ritzlib's `ritz.toml`, #4864) and
3 (`ritz-package.toml`, `rz pack`, `rz install`, the `{ version = … }`
dependency kind, #4865: `projects/ritz/packages.py`) are in. No build links
an archive yet: that is slice 4.

**Amends** [`design/PACKAGING_RFC.md`](design/PACKAGING_RFC.md) §3.2
("Libraries are always source"). Source stays the artefact of record: a
package always ships its full source, and every importer reads it. The
compiled archive beside it is an optional accelerator that a build uses only
after proving it was built from that source, by this compiler, for this
target. When it can't prove that, the build compiles the shipped source, as
it does for a `path` dependency today.

Aaron, 2026-11-27: *"Prebuilt packages need to be packaged with the entire
source, so other things can do the monomorphy bits, and so we can reuse /
link code from those libraries."*

## The rule in one paragraph

A package is a directory holding a library's full source tree, its
`ritz.toml`, a `ritz-package.toml` manifest, and one `lib<name>.a` per object
profile. Importers resolve the package's modules from the shipped source,
exactly as for a `path` dependency, so generics monomorphize and interfaces
strip as they do today. At link time the build recomputes the CAS key
(`cas.module_key`) of every module in the package, under the building
compiler and the binary's object profile, and compares the set with the keys
the manifest recorded when the archive was made. Equal: the build compiles
none of the package's modules and links the archive. Any difference: the
build compiles the shipped source through the CAS and never links that
archive.

## What exists today

| Piece | Where | What this design takes from it |
|---|---|---|
| `path` deps only | `manifest.py:170-185` schema, `resolve.py:87-145` `parse_dependencies`, `DependencySpec` `resolve.py:49` | A package resolves to a `DependencySpec` whose `path` is its install directory. Nothing downstream of `DependencySpec` changes for imports. |
| `[[lib]]` archive | `build_pipeline.py:1646-1720` `compile_library` | Already writes `lib<name>.a` from CAS objects, with a provenance file listing each module's CAS key. `rz pack` reuses it. No link consumes the archive today. |
| Binary link | `compile_binary` `build_pipeline.py:1463-1592`, `compile_modules` :1303, `link_hosted` :1422-1461 | One `.o` per module of the import closure (`discover_modules` :1085), all passed to clang. The archive goes in here. |
| Test link | `ritz0/test_runner.py:660` `_link`, :925 | Test binaries link ritzunit and ritzlib objects the same way. This is the second consumer, and the bigger one. |
| CAS key | `cas.py:254-290` `module_key`, `build_pipeline.py:372` `cas_module_key`, :540 `_cas_key` | Covers compiler fingerprint (`cache.compute_compiler_hash`: the binary plus the `RITZ0_DRIVER_FILES`, `cache.py:60`), `cas.target_id()` (OS, machine, `clang --version`), object flags (`Target.key_flags`), the module's identity and source sha256, and its imports' interface hashes. "Equal keys prove equal objects" (`compile_library`'s own comment). The stamp check is this key. |
| Module interfaces | `ritz0/module_interface.py`, ritz1 `strip_to_interface` (`ritz1/src/main.ritz`) | Keep generic, async and inline bodies, so an importer has what it needs to monomorphize from source. Unchanged. |
| Generic instances | #4609 | Internal copies in each importer's object. An archive never exports them, so it never needs to know who instantiates what. |
| Archive linking precedent | `tools/run_regression_matrix.py:485-500` `baseline_archive` | Links ritzlib's objects as one archive so `ld` pulls a member only for a symbol nothing else defines. Same semantics as here. |
| Location-bound symbols | `ritz0/emitter_llvmlite.py:648` `symbol_file_key`, ritz1 `ritz1/src/diag.ritz:289`; `cas.py:168` `module_identity`; `build_pipeline.py:512` `_path_bound_modules` | A private fn's symbol hashes its file's path relative to the nearest `.git`, else the absolute path. This is the one thing that breaks a prebuilt archive today (see "Identity"). |

## 1. Package layout

```text
<install root>/ritzlib/0.1.0/
├── ritz-package.toml          # manifest, written by `rz pack`
├── ritz.toml                  # the package's own manifest, as in its repo
├── <every source file>        # the full tree [[lib]] compiles, byte for byte
│   ├── fs.ritz
│   ├── fmt/…
│   └── …
└── lib/
    ├── hosted/libritzlib.a                 # Linux x86_64 user programs
    └── harland-user-<k8>/libritzlib.a      # one per freestanding profile
```

The source tree is the package's `[[lib]]` module set: what
`compile_library` compiles, plus nothing it excludes (`!tests` and the like).
Tests, docs and examples stay out, as `projects/builder/stage_tree.py`
already does for the builder image.

A **profile** is one value of `Target.key_flags` (`build_pipeline.py:1045`):
`None` is `hosted` (`OBJ_CLANG_FLAGS` = `-c -O2 -fPIC -ffreestanding
-fno-builtin`), and each freestanding target (harland kernel, Indium user
programs, UEFI) is `<target_os>-<first 8 hex of sha256(key_flags)>`. The
`[profile.*]` opt-level, debug and lto settings are not a profile axis: they
reach only the link (`link_hosted` :1443-1450), never the objects, so one
`hosted` archive serves debug and release builds alike. `-march=native` is a
link flag too, so an archive is not CPU-specific.

`ritz-package.toml`:

```toml
[package]
name = "ritzlib"
version = "0.1.0+g562ea1330"
# sha256 over the sorted (relative path, sha256) of every source file.
source_sha256 = "…"

# Each shipped source file and its sha256. `rz install` verifies them; the
# build does not need to, because the CAS keys below already cover them.
[source]
"fs.ritz" = "…"
"fmt/int.ritz" = "…"

# The package dependencies it was packed against, by name, version and
# source_sha256. A path dependency is packed first and named here.
[dependencies]
# ritzunit's manifest would say:
# ritzlib = { version = "0.1.0+g562ea1330", source_sha256 = "…" }

[[archive]]
profile = "hosted"
path = "lib/hosted/libritzlib.a"
archive_sha256 = "…"
compiler = "ritz1_selfhosted"
compiler_fp = "…"        # cache.compute_compiler_hash, as the CAS uses it
target = "linux/x86_64/clang version 20.1.8 …"  # cas.target_id()
triple = "x86_64-unknown-linux-gnu"
object_flags = {}        # Target.key_flags; empty for hosted

# Per module: its CAS key (the stamp), its object's sha256 and the archive
# member holding it (for `rz install --verify`, which rebuilds and compares).
[archive.modules]
"fs.ritz" = { key = "…", object_sha256 = "…", member = "fs_1a2b3c4d.o" }
```

`compiler_fp`, `target`, `triple` and `object_flags` are redundant with the
keys. They are there so a mismatch can say *why* in one line ("built by
ritz1_selfhosted 3f2a…, this is 9c1d…") without re-deriving keys, and so the
check can reject cheaply before computing any key.

## 2. Naming an installed package

### In `ritz.toml`

A new dependency kind beside `path`, added to the schema at
`manifest.py:170-185` (so `docs/RITZ_TOML_SPEC.md` regenerates):

```toml
[dependencies]
# Today: source from a directory.
ritzlib = { path = "../ritz/ritzlib" }

# New: an installed package, by exact version.
ritzlib = { version = "0.1.0+g562ea1330" }

# Optional: pin the source tree, so a reinstall with other content fails.
ritzlib = { version = "0.1.0+g562ea1330", source_sha256 = "…" }
```

`path` and `version` are mutually exclusive. v1 has exact versions only: no
ranges, no resolver, one version of a name per build (two that differ is an
error naming both requirers). `prebuilt = false` on either kind forces source
for that dependency, for bisecting a suspected archive problem.

**A `path` dependency whose directory holds a `ritz-package.toml` is a
package too.** The decision to use an archive comes from the directory's
contents and the stamp, never from the syntax that named it. The builder
image uses this: it ships ritzlib as a package at the path every in-tree
`ritz.toml` already names (`../ritz/ritzlib`), so buddhafinger's `ritz.toml`
does not change. A dev checkout has no `ritz-package.toml` in
`projects/ritz/ritzlib` (`rz pack` writes it only into the staged tree, and
it is `.gitignore`d), so in-tree builds are exactly today's.

### Resolution

`parse_dependencies` (`resolve.py:87`) turns `{ version = … }` into the same
`DependencySpec(name, path, sources)` a path dep gets, with `path` the
install directory and `sources` from the package's own `ritz.toml`, plus one
new optional field: `package: PackageInfo | None`, the parsed
`ritz-package.toml`. `package_import_namespaces`, `RITZ_PATH`, `list_deps`
and the per-module import context read `name`, `path` and `sources` only, so
they need no change.

### Where installs live

`$RITZ_PACKAGES/<name>/<version>/`, default
`${XDG_DATA_HOME:-~/.local/share}/ritz/packages`. Data, not cache: deleting
it breaks builds, unlike `$RITZ_CACHE_DIR` (`~/.cache/ritz/cas`), which a
build refills. The builder image sets `RITZ_PACKAGES=/rz/packages`.

### `./rz pack` and `./rz install`

No registry in v1, and no network at build time.

```text
./rz pack ritzlib [--profile hosted] [--profile harland-user] [--version V] -o ritzlib-V.tar.gz
./rz install ritzlib-V.tar.gz
./rz install https://…/ritzlib-V.tar.gz --sha256 <tarball sha256>
./rz install --verify ritzlib 0.1.0+g562ea1330
./rz uninstall ritzlib 0.1.0+g562ea1330
```

- **pack** copies the `[[lib]]` module set into a staging directory, writes
  the marker, builds each requested profile's archive *from the staged tree*
  with `compile_library`, records keys and object hashes, and tars it. It
  refuses a package whose path dependencies aren't packed (it names them)
  and rewrites them into `[dependencies]` as name, version and
  source_sha256. `--version` defaults to the `ritz.toml` version plus
  `+g<12 hex of HEAD>` in a checkout, so two packs of different trees never
  share a version.
- **install** extracts with `tarfile`'s `data` filter (no absolute paths, no
  `..`, no links out, no devices) into a temp dir under `$RITZ_PACKAGES`,
  checks every `[source]` hash and every `archive_sha256`, then
  `os.replace`s it into place, as the CAS publishes (`cas.py`, "Concurrency").
  An existing `<name>/<version>` with a different `source_sha256` is an
  error. A URL is fetched with `urllib` to a temp file first; `--sha256` is
  required for a URL.
- **install --verify** rebuilds every archive member from the shipped source
  through the CAS and compares `object_sha256`. A clang `-c` of identical IR
  is deterministic, so a mismatch means the archive was not built from this
  source. CI runs it on every pack it publishes. The build itself does not:
  the stamp proves which inputs the objects claim; `--verify` proves the
  claim.

## 3. Import resolution: unchanged

An importer reads the package's shipped `.ritz` files, as for any
dependency. ritz0 builds `module_interface` from them; ritz1 runs
`strip_to_interface` on them. Generic, async and inline bodies survive into
the interface, so `Vec<T>` instantiated in buddhafinger is emitted in
buddhafinger's object (#4609), and the archive's members are only the
package's own non-generic code. Nothing in ritz1's import path changes, and
no compiler reads `ritz-package.toml` except through the identity rule below.

### Identity: the one compiler change

Two things name a module by where it sits on disk, and a prebuilt archive
breaks both today:

1. **Private fn symbols.** `symbol_file_key` (ritz0
   `emitter_llvmlite.py:648`, ritz1 `diag.ritz:289`) hashes the file's path
   relative to the nearest `.git`, else its absolute path. An installed
   package has no `.git` above it. When buddhafinger instantiates a ritzlib
   generic whose body calls a private ritzlib fn, buddhafinger's object
   names that fn's symbol with the hash of
   `~/.local/share/ritz/packages/ritzlib/…/hashmap.ritz`. The archive, built
   in pack's staging directory, defines it under the hash of the staging
   path. The link fails with an undefined `helper__<hash>`, the same failure
   `_path_bound_modules` (`build_pipeline.py:512`) was added for.
2. **CAS module identity.** `cas.module_identity` (`cas.py:168`) is the
   repo-relative path, else `ext/<file name>`. Keys of installed modules
   would differ from the keys pack recorded, so every stamp check would fail.

The fix is one rule, in both places and in both compilers: **a file under a
directory holding `ritz-package.toml` is named `pkg/<package name>/<path
relative to that directory>`**, and that marker wins over a `.git` further
up. The package name is in the key so two packages' `util.ritz` private fns
stay distinct. Then pack's staging tree and every install name every module
and every private symbol alike, keys computed at pack time are the keys the
importer computes, and the CAS shares objects between installs.
`_path_bound_modules` skips `pkg/` modules, as it skips in-repo ones.

DWARF `DIFile` carries the same relative name, so a debugger finds the source
in the install directory with `directory` or `set substitute-path`.

## 4. Linking

### The swap

`compile_binary` (`build_pipeline.py:1463`) after `discover_modules`:

1. For each dependency with `package` set, find the `[[archive]]` for this
   binary's profile (`Target.key_flags`). None: source.
2. Cheap reject: `compiler_fp`, `target` and `object_flags` against the
   building compiler's (`cache._get_current_compiler_hash()`,
   `cas.target_id()`). Different: source, with a one-line reason.
3. Stamp: `cas_module_key` for every module in the package's
   `[archive.modules]`, compared as a set. Equal: use the archive. The key
   covers the source bytes, so an edited install falls back, and the
   imports' interface hashes, so ritzunit packed against one ritzlib and
   linked against another falls back. The closure memo (#1920) makes a
   repeat check a lookup per module.
4. Archive in use: drop the package's modules from the list `compile_modules`
   gets, and pass the archive to the link. Archive refused: compile the
   package's modules from the shipped source through the CAS (today's path),
   and archive those objects (step "Fallback" below).

All or nothing per archive: never some members from the archive and others
from source.

`link_hosted` (`:1422`) takes `archives` beside `link_files`:

```text
clang <runtime _start.o> <own objects…> -Wl,--start-group libritzunit.a libritzlib.a -Wl,--end-group -o … -nostdlib …
```

The group removes any need to order archives by dependency. Members are
pulled by symbol, as with `baseline_archive`, so unreferenced ritzlib modules
drop out of the binary. One behaviour changes and is intended: an importer
that defines a symbol a package module also defines (a test's own `strlen`)
now wins instead of failing with a duplicate symbol, the case
`baseline_archive`'s docstring records.

### Fallback links an archive too

When the stamp fails, the build compiles the package's modules and `ar`s
their objects (sorted by module identity) into a scratch archive, then links
it the same way. One link rule for both paths means a binary built against
the prebuilt archive and one built from source differ only if their objects
do, and with equal keys they can't: the epic's "output matches a from-source
build" test can assert byte equality, not just equal test verdicts. It also
makes the swap visible to the existing up-to-date check:
`binary_provenance` (`:915`) records each package's `archive_sha256` (or the
scratch archive's) beside the source hashes it already lists.

### Tests

`ritz0/test_runner.py` `_link` (`:660`) and its dependency-object loop get
the same swap: the test harness links ritzunit and ritzlib, which is where
`rz test` spends its cold time. ritz1 test builds go through the same Python
driver, so they follow.

### Freestanding

`compile_freestanding_binary` (`:1969`) keys modules with its `Target`'s
`key_flags`, so it looks up `profile = <target_os>-<k8>` and applies the
same swap; its link is `ld.lld` with a linker script, and the archives go
after the objects inside a `--start-group`. A package without that profile
compiles from source. The harland kernel's flags (`stack_protector`,
`no_red_zone`) make it a profile of its own; Indium's user programs share
another.

### LTO

`lto = true` adds `-flto` to the link (`:1449`), but CAS objects are native
`clang -c -O2` objects, not bitcode, so it has nothing to optimise across
today, archive or not. An archive does not change that. Bitcode members are
future work, if `lto` ever means anything here.

### The CAS (#4857)

The two meet in the key and stay separate stores:

- **#4857 persists the CAS** across CI runs. It saves the same compiles, but
  only on a host or cache that has already compiled them with this compiler,
  and only after one cold run per compiler change.
- **A package is the same objects, distributable.** It works on a cold CAS:
  a fresh machine, the first build after a new builder image, an offline
  box, a user who never built ritzlib. Its stamp *is* a CAS key, so the
  rules can't drift apart.
- `rz install` seeds nothing into the CAS. The CAS's entries are what this
  host compiled; an archive's members are what pack compiled. `--verify` is
  where the two are compared.

Considered and not chosen: a package that ships CAS objects instead of an
archive, so `rz install` fills the store and the link doesn't change. It
needs no link work, but it isn't a library a binary links (Aaron's ask), it
puts other hosts' objects in this host's store unverified, and test and
freestanding builds would still link every closure object.

## 5. ritzlib as the first package

Done in slice 2 (#4864). ritzlib had no `ritz.toml`, so dependents named it
as `{ path = "../ritz/ritzlib", sources = ["."] }`. It now has:

```toml
# projects/ritz/ritzlib/ritz.toml
[package]
name = "ritzlib"
version = "0.1.0"
sources = [".", "!tests"]

[[lib]]
name = "ritzlib"
```

`ritzlib/tests/` keeps its own `ritz.toml` and stays a separate test package.
`rz build ritz/ritzlib` archives all its modules as `libritzlib.a`, and
`rz build --all` now builds it, so a module that fails to compile for
`hosted` fails the sweep even when nothing imports it. In-repo dependents
dropped their `sources = ["."]`; it still works (it overrides). A `!path`
entry gets no ritz1 `--dep` (`ritz1_compile_cmd`).

**ritzunit is the second.** It path-depends on ritzlib and on itself
(`ritzunit = { path = "." }`); pack turns the ritzlib dep into a package
reference and drops the self-reference, which the marker's identity rule
covers.

### Consumers

- **Builder image** (`projects/builder`). `stage_tree.py` copies ritzlib and
  ritzunit as sources today, and every container compiles both again
  (`entrypoint.sh:250`, a fresh `$WS/cas`). The image build runs `rz pack`
  for ritzlib and ritzunit with the image's own `ritz1_selfhosted`, `hosted`
  and the harland profiles, and stages the *packed* trees at their usual
  paths. Packed with the image's compiler, the stamp always matches inside
  that image; a checkout mounted as `$RZ_ROOT` (#4847) brings its own
  unpacked ritzlib, so the image's archives never meet another tree's
  source. Every buddhafinger build and test in the image then compiles only
  buddhafinger.
- **Indium staging** (`projects/indium/initramfs.pkgs`, staged by
  `projects/indium/tools/stage_initramfs.sh`; buddhafinger's entry builds in
  the builder image, AGAST #4834). Each listed package builds its ELFs freestanding and
  compiles ritzlib for Harland again. With a harland-user archive in the
  ritzlib package, each package compiles only its own modules. In-tree,
  `make -C projects/indium` would `rz pack ritzlib --profile harland-user`
  into `build/packages` once per compiler and point `RITZ_PACKAGES` there.

## 6. Measured payoff

buddhafinger, cold, `ritz1_selfhosted`, measured 2026-11-27 on huburght at
`f40a1474e` (WSL2, 12 CPUs, load 21-27 from other rooms, so read the wall
times as ±50%). Cold means fresh `RITZ_CACHE_DIR` and `RITZ_BUILD_CACHE_DIR`.
A single-package build compiles one module at a time. Per-module times come
from timestamping every compiler and `clang -c` subprocess and assigning it
to its `.ritz` source, which accounts for about 95% of the wall time.

| Run | Wall | own modules | ritzlib | ritzunit | link + rest |
|---|---|---|---|---|---|
| `rz build`, cold (two runs) | 8.7-15.0 s | 10, 3.5-7.3 s (41-50%) | 15, 3.1-5.5 s (36-38%) | none | link 0.2-0.5 s, `list_deps` ~1 s |
| `rz test`, cold | 38.7 s | 16 (10 src + 6 test), 15.3 s (40%) | 26, 16.4 s (43%) | 8, 4.5 s (12%) | links ~1.3 s, suite ~0.7 s |
| `rz test`, warm CAS | 7.1 s | | | | suite 5.1 s |

- **What the archive saves:** every ritzlib and ritzunit compile. That is
  about 37% of a cold build and **55% of a cold test run (~21 s of 39 s)**.
  A builder-image container does both on a cold CAS every time
  (`entrypoint.sh:250`), so its run drops from roughly 45 s to roughly 22 s.
- `clang -O2` is about 90% of each module's compile time. ritzlib's cost sits
  in a few modules: string 0.84 s, strview 0.70 s, sys 0.57 s, memory 0.47 s
  and str 0.45 s of clang time.
- A warm CAS does better still (7.1 s: it skips own modules too). So on one
  host the archive adds nothing over #4857's persisted CAS. It pays where a CAS can't be
  warm: a new compiler's first run (every builder image), each Indium
  package's harland build of ritzlib, a fresh machine, and every package in
  the builder matrix sharing one prebuilt ritzlib rather than one cache.
- These are one package's numbers. The saving per run is roughly fixed (the
  ritzlib + ritzunit closure a package reaches), so it is a large share for
  small packages and a small one for big ones.

## Slices (filed after the OK)

Each is one commit with its own tests; the order is the dependency order.

1. **Identity.** The `ritz-package.toml` marker in `symbol_file_key` (ritz0,
   ritz1) and `cas.module_identity`; `_path_bound_modules` skips `pkg/`.
   Test: a generic in a marked package calling a private fn, compiled in two
   directories, links across them.
2. **ritzlib's `ritz.toml`** and `[[lib]]`; `rz build ritzlib` builds
   `libritzlib.a`; dependents' `sources = ["."]` optional.
3. **pack / install / dep kind.** `ritz-package.toml` schema, `rz pack`,
   `rz install` (file, URL + sha256, `--verify`), `{ version = … }` and
   `prebuilt = false` in the schema and `parse_dependencies`. Done (#4865):
   `packages.py`, tested by `tools/test_packages.py`. As built: pack packs
   the `hosted` profile only (a freestanding profile needs its `Target`
   from a consumer, slice 5); each `[archive.modules]` entry also records
   its `member` name, so `--verify` compares the archive's own bytes with
   the rebuild; a tree with uncommitted changes packs as
   `+g<sha>.dirty<8 hex of source_sha256>`; install refuses any tarball
   member that is not a regular file or directory, and any file the
   manifest does not list. Two things still named a module's directory in
   its object, so a cold-store rebuild in an install differed from pack's
   bytes: ritz0's DWARF `DIFile` directory (now `pkg/<name>/<dir>` in a
   package, `debug_source_dir`) and the artefact name `compile_modules`
   hashed from the absolute path, which clang records as the object's
   `STT_FILE` and `ar` as the member name (now hashed from the identity).
4. **Link swap.** Stamp check, archive link with fallback archive, in
   `compile_binary`, `test_runner`, `compile_freestanding_binary`;
   `binary_provenance` records archives. Tests: a matching stamp compiles
   zero package modules; a changed compiler fingerprint, an edited shipped
   source and a mismatched dependency each fall back with their reason; the
   two binaries are byte-equal.
5. **Consumers.** The builder image ships packed ritzlib and ritzunit;
   Indium packs a harland-user ritzlib. Epic done: buddhafinger builds and
   tests against the installed package, links the archive, matches the
   source build, and a compiler mismatch falls back.

## Open questions for Aaron

1. **Exact versions only in v1**, with `+g<sha>` from pack. Enough until a
   second consumer outside the monorepo exists?
2. **"A path dependency that holds `ritz-package.toml` is a package."** This
   is what lets the builder image use archives with no `ritz.toml` edits.
   The alternative is `{ version = … }` everywhere a package is wanted, and
   in-repo dependents keep `path`.
3. **Strict stamp.** The compiler fingerprint includes the driver files
   (`build.py`, `build_pipeline.py`, …, `cache.py:60`), as the CAS's does, so
   any driver edit refuses every archive. Safe, and invisible in the builder
   image (one compiler per image); in a dev checkout, archives help only
   between driver edits. Narrowing the fingerprint is a CAS-wide change and
   out of scope here.
