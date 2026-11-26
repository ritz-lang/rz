# builder: the Ritz builder image

A Docker image holding `ritz1_selfhosted`, `rz` and the Ritz sources a
package imports, plus only the native tools a build calls. It builds and
tests one package and will become the CI unit (AGAST epic #4783; this
directory is #4822).

```bash
bash projects/builder/test.sh                  # build from HEAD's tree, test it, remove it
bash projects/builder/test.sh --keep <commit>  # same for <commit>; keep the image
bash projects/builder/test.sh --reproducible   # also rebuild the bootstrap with no cache
```

`test.sh` passes `git archive <commit>` to `docker build` as the context, so
the image comes from a clean tree at one commit, never from a working tree.
It builds in two passes (the second labels the image with the first's
`ritz1_selfhosted` sha256), then runs checks inside the image. The image is
tagged `rz-builder:<commit12>-<ritz1-sha12>` and labelled
`dev.ritz.rz.commit` and `dev.ritz.ritz1-selfhosted.sha256`.
`/rz/BUILDER_INFO` in the image records those values and the clang and
binutils versions.

Inside the image the workspace is `/rz`. The entrypoint builds and tests
one package with that image's `ritz1_selfhosted` (passed as `RITZ1` and as
`--compiler ritz1_selfhosted`, never the default compiler) and writes
`/out`:

```bash
# A mounted package. Path dependencies and ritzlib come from the image.
# seccomp=unconfined: Docker's default profile returns EPERM for
# io_uring_setup / io_uring_enter / io_uring_register, and ritzlib's tests
# call them.
docker run --rm --network=none --security-opt seccomp=unconfined \
    -v "$PWD/projects/sage:/src/projects/sage:ro" \
    -v "$PWD/out:/out" \
    rz-builder:<tag> /src/projects/sage

# A package that already ships in the image.
docker run --rm --network=none --security-opt seccomp=unconfined \
    -v "$PWD/out:/out" \
    rz-builder:<tag> projects/sage

# Harland's kernel ELF, build only. The image has no QEMU.
docker run --rm --network=none --security-opt seccomp=unconfined \
    -v "$PWD/out:/out" \
    rz-builder:<tag> --build-only projects/harland
```

The exit status is 0 only when the build succeeded and every test passed.
`--build-only` skips tests and is 0 when the build succeeded. The source
mount is not written. The run needs no network.

`/out` holds `bin/` (ELF and PE binaries), `obj/` (this run's `.o` files),
`build/` (the package build tree), `build.log`, `test.log`, and
`summary.json` (`ok`, the build exit, and the test counts). When the
container is root, those files are given to the user who owns the mount.

```bash
bash projects/builder/accept.sh rz-builder:<tag>
```

That compares the host's `./rz build` and `./rz test` under
`ritz1_selfhosted` with the container, on ritzlib's tests, sage, rzsh's
Linux bin, tome, one indium PIC bin, and harland's kernel ELF (build
only). The two sides must agree on pass/fail and on the test counts.

Publishing from CI and enforcing the size budget is #4824.

This directory is not a Ritz package and has no `ritz.toml`. `rz`'s
`projects/**` glob only matches directories that have a `ritz.toml`
(`tools/test_nested_packages.py` passes with it present). smoke-plan.sh maps
`projects/builder/**` to its own `builder` target, which runs `test.sh`,
instead of `pkg:builder`.

## Files

| File | What |
|---|---|
| `Dockerfile` | `toolchain` → `bootstrap` → `runtime` (the image) |
| `Dockerfile.dockerignore` | The context filter for a build from a working tree. BuildKit reads `<Dockerfile>.dockerignore`, so it applies to this image only. |
| `check_fixed_point.sh` | Stage 2 == stage 3: ritz1_selfhosted rebuilds itself byte for byte |
| `stage_tree.py` | Copies the runtime tree (below) out of a checkout |
| `collect_toolchain.sh` | Copies the native tools and their `ldd` closure |
| `test.sh` | Builds the image from `git archive` and tests it by running it |
| `entrypoint.sh` | Image entrypoint: one package, `ritz1_selfhosted`, artifacts in `/out` |
| `summary.py` | Writes `summary.json` and copies bins and `.o` files into `/out` |
| `accept.sh` | Host `./rz` versus the container, on the packages #4823 names |

## Survey: what a build executes

Measured on 6892b71c6 by running `./rz build --all` and `./rz test` (squeeze,
ritzunit, an example) under `--compiler ritz1_selfhosted`, with a Python
audit hook (`sys.addaudithook`, via `sitecustomize`) logging every module
loaded, file opened and subprocess started, in `rz` and in every Python
child process.

### Python

`rz` runs `projects/ritz/build.py` as a child for each package, and
`build_pipeline` runs `ritz0/list_deps.py` for the import graph. In-process,
`build_pipeline` imports `ritz0/module_interface` for interface hashes, which
pulls in ritz0's front end: lexer, parser, AST, monomorph. ritz0's back end
(`emitter_llvmlite` and the rest) and llvmlite are **not** loaded when the
compiler is ritz1_selfhosted, so the image has no llvmlite and no ritz0
compiler. `stage_tree.PYTHON_FILES` lists the 34 files: `rz`, nine
`projects/ritz/*.py` modules, `tools/known_failures.py`, and 23 ritz0
modules. Nothing outside the standard library is imported.

The standard library modules include `tomllib`, `shutil`, `tempfile`,
`concurrent.futures`, `uuid`, `lzma` and `bz2`. Debian's `python3-minimal`
lacks those, so the runtime installs `python3-minimal` plus
`libpython3.13-stdlib` (Python 3.13; rz needs ≥ 3.11 for `tomllib`).

### Native tools

| Tool | Called by | When |
|---|---|---|
| `ritz1_selfhosted` | `build_pipeline` (`RITZ1_SELFHOSTED_BIN`, a fixed path) | every `.ritz` → `.ll` |
| `clang` | `build_pipeline` | every `.ll` → `.o`; links hosted binaries (`clang -nostdlib`, which runs `ld`) |
| `ld.lld` | `build_pipeline.find_llvm_tool("lld")` | freestanding links with a linker script (prism, angelo, harland) |
| `lld-link` | `build_pipeline` | UEFI PE/COFF links (harland's bootx64) |
| `llvm-ar` (`ar` fallback) | `compile_library` | `[[lib]]` archives |
| `as` (binutils) | `build_pipeline` | freestanding `.s` files (harland kernel) |
| `ld`, `readelf`, `objcopy` (binutils) | `build_testrun` | `rz test`'s ritzunit runner: `ld -r`, symbol listing, `--keep-global-symbols` |
| `bash` | `build_testrun` | a package's `test.sh` |

`make` is not called by `rz build` or `rz test`; it only builds ritz1, in the
bootstrap stage. `opt`/`llvm-as` run only under `RITZ_VERIFY_IR`, a gate
option, so they do not ship (add them to `collect_toolchain.sh`'s list in the
Dockerfile if the CI unit turns it on; both link the `libLLVM` already
shipped). `find_llvm_tool` tries versioned names only up to `-20`, so it
would miss `llvm-ar-21`. The image avoids that the way CI does: the unversioned
names live in `/usr/lib/llvm-21/bin`, which comes first on `PATH`.

clang is LLVM 21, CI's `CLANG_VERSION` (`.github/workflows/main.yml`,
installed by `.github/actions/setup` from the distro or apt.llvm.org).
Debian 13 has no clang-21, so the image uses apt.llvm.org's
`llvm-toolchain-trixie-21`, with the signing key pinned by checksum.

### Ritz sources

- **ritzlib** (`projects/ritz/ritzlib`, without `tests/`): every hosted
  package imports it, through `RITZ_PATH` or a `ritzlib = { path = … }`
  dependency.
- **The runtime shims** (`projects/ritz/runtime/ritz_start*.ll`): every
  hosted binary links `_start` from them.
- **Library packages**: every package that some `ritz.toml` names as a path
  dependency, found by reading the manifests (`stage_tree.library_packages`),
  plus ritzunit, which `rz test` links into every test binary, and the
  harland kernel package. Nothing path-depends on `projects/harland` itself
  (the dependencies name its ABI subdirectories), and the entrypoint builds
  that kernel ELF with `--build-only`. The image has no QEMU. On
  6892b71c6 that is angelo, cryptosec, goliath, harland's boot_abi,
  driver_abi, libnet, net_abi and virtio_abi, http, iris, lexis, mausoleum,
  prism, ritzunit (with inventory), sage, spire, squeeze, tome and zeus.
  projects/ritz is also one (tempest names `../ritz`), but only its
  `ritz.toml`, ritzlib and the shims ship.
- From each package: `ritz.toml` and the `.ritz`, `.ld`, `.s`, `.S` and
  `.ll` files. Directories named `test`, `tests`, `docs`, `bench`, `build`,
  `fixtures` and similar are dropped, unless the package's own manifest
  lists that directory as a `sources` root (mausoleum, spire, tome and zeus
  build bins from `test/` or `examples/`).
- `known-failures/*.toml`: `rz build --all` reads its verdicts from them.
- `rz.toml`: written by `stage_tree.write_workspace` from the checkout's
  copy. It drops the members and exclusions that name paths the image does
  not ship, because rz rejects a member glob that matches no package
  (`bench/regressions/...`) and an exclusion that excludes nothing.

`test.sh` checks that this is complete by running
`rz build --all --compiler ritz1_selfhosted` in the image: every shipped
package must build.

### ritz1_selfhosted at runtime

```
INTERP   /lib64/ld-linux-x86-64.so.2
NEEDED   libc.so.6
```

It has no undefined dynamic symbols. ritz1's Makefile links it with
`ld … -lc`, which records `NEEDED libc.so.6` anyway, so the loader still has
to find a glibc `libc.so.6`. Hosted Ritz binaries built in the image request
the same interpreter, with no `NEEDED` entries.

### Base image: glibc, not musl

Alpine would need `gcompat` or glibc's loader for ritz1_selfhosted, and its
clang defaults to `/lib/ld-musl-x86_64.so.1` as the interpreter, so hosted
binaries built there would differ from CI's. Alpine's Python and LLVM are
also musl builds, different from the ones CI tests with. A glibc base avoids
all three, so the base is `debian:trixie-slim`, pinned by digest: Debian 13,
glibc 2.41, about 78 MB unpacked.

## The bootstrap stage

1. `toolchain`: the base, apt.llvm.org's clang-21, lld-21 and llvm-21,
   binutils, make, and python3 with venv.
2. `bootstrap`: llvmlite pinned by `projects/ritz/requirements.lock`, then
   `make -C projects/ritz ritz1-bootstrap`. ritz0 builds ritz1 (stage 1),
   and ritz1 builds ritz1_selfhosted (stage 2).
3. `check_fixed_point.sh`: ritz1_selfhosted rebuilds ritz1 through ritz1's
   own Makefile (same modules, ritzlib objects, link order and flags; only
   `RITZ1` and `BUILD_DIR` differ) into stage 3, and the build fails unless
   stage 3 is byte-identical to stage 2. On 6892b71c6 all 89 modules'
   IR matched and the binaries were the same file.
4. `stage_tree.py` writes `/stage` (the tree above), and
   `collect_toolchain.sh` writes `/toolchain`: the tools from the table and
   their `ldd` closure, without libc6's own files.

Only `/stage` and `/toolchain` reach the image. The compiler-building
toolchain (llvmlite, make, the clang-21 package's ~460 MB of dependencies:
libc6-dev, libstdc++-dev, gcc's sanitizer runtimes) stays in the throwaway
stages.

## Size

Measured on huburght (Docker 29.1.3, containerd image store), at 6892b71c6
plus this directory:

| | |
|---|---|
| Unpacked filesystem (`du -sxk /` in the image) | **353 MiB** |
| Compressed content (what a pull transfers) | 124 MB |

| Layer | Unpacked |
|---|---|
| `debian:trixie-slim` | 88 MB |
| Python 3.13 (`python3-minimal` + `libpython3.13-stdlib`) | 31 MB |
| Native tools + `ldd` closure | 243 MB, of which libLLVM 140 MB, libclang-cpp 61 MB, libz3 28 MB (libLLVM needs it), clang/lld/llvm-ar 6 MB, binutils ~4 MB |
| `/rz`: rz, Python modules, Ritz sources, ritz1_selfhosted (2.5 MB) | 9.6 MB |

**Budget: 400 MiB unpacked**, about 13% above the measurement. `test.sh`
fails above it. The budget is on the unpacked size measured inside the image
because `docker image inspect`'s `.Size` is the compressed size under the
containerd image store and the unpacked size under overlay2, so it means
different things on different hosts.

LLVM's shared libraries are two-thirds of the image. They go away when the
razm/rllvm/rld cutover removes clang and lld from ELF builds (epic #4783,
"LATER"). Until then, the only large cut would be a static, trimmed clang
build, which is a toolchain project of its own. The Python layer could
shrink by about 10 MB with a hand-picked stdlib, which isn't worth maintaining.
