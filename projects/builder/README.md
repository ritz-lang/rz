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

A whole checkout can stand in for the image's sources (AGAST #4847): mount
it read-only and name it as `RZ_ROOT`, and pass the package's in-tree path,
under `projects/` or not. The compiler is still the image's
`ritz1_selfhosted`, linked into the private workspace; the checkout's own
`ritz1/build` is never used. That is how main.yml's `builder-matrix` runs
each package in its list (`.github/scripts/run_builder_package.sh`): a
package's tests may read files the image doesn't ship (prism reads angelo's
font fixture, buddhafinger ritz1's keyword table).

```bash
docker run --rm --network=none --security-opt seccomp=unconfined \
    -e RZ_ROOT=/ws -v "$PWD:/ws:ro" \
    -v "$PWD/out:/out" \
    rz-builder:<tag> projects/prism
```

The exit status is 0 only when the build succeeded and every test passed.
`--build-only` skips tests and is 0 when the build succeeded. The source
mount is not written. The run needs no network.

`/out` holds `bin/` (ELF and PE binaries), `obj/` (this run's `.o` files),
`build/` (the package build tree), `build.log`, `test.log`, and
`summary.json` (`ok`, the build exit, the test counts, and `cas`: the
store's hits, misses and the modules it `compiled`), and `cas-stats.jsonl`
(the store's per-process record, `cas.py summary` reads it). When the
container is root, those files are given to the user who owns the mount.

### A persistent CAS (`RZ_BUILDER_CACHE`)

By default the CAS (the compiled modules: the package's own, ritzlib's,
ritzunit's) lives in the run's private workspace and is gone after it.
Mount a writable directory and name it in `RZ_BUILDER_CACHE` to keep it
(AGAST #4857):

```bash
docker run ... -v "$PWD/cas:/cache" -e RZ_BUILDER_CACHE=/cache rz-builder:<tag> projects/buddhafinger
```

The store is `/cache/<key>`, where `rz-builder --cache-key` prints the key:
`ritz1-<first 16 of the dev.ritz.ritz1-selfhosted.sha256 label>-clang-<version>`.
A new compiler starts an empty store and deletes the other `ritz1-*` ones.
After the run the store is trimmed to `RZ_BUILDER_CACHE_MAX_BYTES` (`cas.py
gc`; default 1536MiB). Reuse is safe by construction: a CAS key covers the
compiler, clang, the flags and every source in a module's import closure.
Concurrent runs on one store are safe too (atomic renames, a per-key lock).
Anyone who can write the directory can plant objects a later run links in,
so mount it writable only for trusted builds. The entrypoint works in a
fixed `/tmp/rz-builder-ws`: the package's own modules are keyed by their
absolute path, and a random workspace missed them on every run.

buddhafinger on the hosted path, 2026-11-27: cold 16 s and 55 modules
compiled; warm 3 s and 0 compiled; the same 156 tests passed, and the same
bins and objects, byte for byte. `test.sh` checks the same on its hello
package, and that a changed compiler misses.

main.yml's hosted `builder-matrix` keeps the directory in `actions/cache`
(`run_builder_package.sh --cache`), keyed by `--cache-key` and saved after
every run. `.woodpecker/builder.yml`'s package steps mount adele's PVC
`rz-builder-cas` (namespace `woodpecker-steps`, local-path, 2Gi, reclaim
`Delete`) at `/cache`. That needs the repo trusted for volumes and every PR
approved before it runs (Aaron, 2026-11-27): a PR's pipeline could otherwise
write objects a later `main` build links in. A cache the run can't write
warns and runs uncached.

```bash
bash projects/builder/accept.sh rz-builder:<tag>
```

That compares the host's `./rz build` and `./rz test` under
`ritz1_selfhosted` with the container, on ritzlib's tests, sage, rzsh's
Linux bin, tome, one indium PIC bin, and harland's kernel ELF (build
only). The two sides must agree on pass/fail and on the test counts.

main.yml's `builder-image` job builds the image of every commit it
validates with `test.sh`, for that run's `builder-matrix` (AGAST #4847). For
a push to main it publishes that image as `:<commit>` alone, for huburght's
Woodpecker (#4846, below). Every other tag comes from
`.github/workflows/builder.yml` (#4824), out of band from the compiler CI. Each run builds and tests the image
with `test.sh`, including its size budget. A push of any git tag publishes
`ghcr.io/ritz-lang/rz-builder:<tag>`, `:ritz1-<sha12>` and `:<commit>`; the
tag is sanitised to a Docker tag, and one that would land on `main`,
`ritz1-*` or a commit is refused. A push to main that changes this directory
publishes `:main` and `:<commit>`. A manual run builds, tests and dry-runs,
and pushes nothing.

### Image versioning by content (AGAST #4903)

`projects/ritz/tools/builder_src_key.py` hashes exactly what the Dockerfile's
`bootstrap` stage builds from and `stage_tree.py` copies into `/stage`: ritz0,
ritz1, ritzlib, the runtime shims, `requirements.lock`, the builder's own
recipe (`Dockerfile`, `stage_tree.py`, `check_fixed_point.sh`,
`collect_toolchain.sh`), and every library package some shipped package
path-depends on (read from `stage_tree.library_packages()`, not a second
hand-maintained list, so the two cannot drift apart). `projects/buddhafinger`
and every other `builder_matrix.MATRIX_PACKAGES` entry is deliberately not an
input: nothing ships them (they build from the mounted checkout,
`RZ_ROOT`/the entrypoint's source mount, never `/rz`), so a commit touching
only one of them computes the same key as its parent.

main.yml's `builder-image` job computes this commit's key before building.
On a push to main, if `ghcr.io/ritz-lang/rz-builder:src-<key>` is already in
ghcr (an earlier commit with the same key published it), the job skips
`test.sh` entirely and retags that image for this commit with `docker buildx
imagetools create` -- a registry-side operation, seconds, not the ~4 min
`test.sh` bootstrap. Otherwise it builds and tests as before and publishes
`:src-<key>` alongside `:<commit>`, so the next commit with this key can take
the fast path.

Woodpecker's `wait-for-image` step still polls for `:<commit>` specifically
(unchanged by this ticket): once the key stops moving, `builder-image`'s
retag makes that tag appear in seconds instead of minutes, which is what
buddhafinger's step was actually waiting on. The alternative -- resolving
`:src-<key>` from the Woodpecker checkout and having the per-package step
pull that tag directly, skipping the GitHub Actions round trip altogether --
was not taken: Woodpecker's kubernetes backend resolves a step's `image:` at
pipeline-definition time from `CI_*` built-ins, and `.woodpecker/builder.yml`
is generated once per matrix change (`builder_matrix.py woodpecker --write`),
not computed per run, so there is no step-to-step channel to feed a
checkout-computed tag name into a later step's `image:` without a second
generated pipeline variant. Keeping the per-package `image:` pinned to
`:<commit>` and making that tag appear fast is the smaller, more honest fix.

This directory is not a Ritz package and has no `ritz.toml`. `rz`'s
`projects/**` glob only matches directories that have a `ritz.toml`
(`tools/test_nested_packages.py` passes with it present). smoke-plan.sh maps
`projects/builder/**` to its own `builder` target, which runs `test.sh`,
instead of `pkg:builder`.

## CI on huburght's Woodpecker

AGAST #4846 (Aaron, 2026-11-26). The per-package matrix runs on the
Woodpecker at `https://ci.fucken.ninja` (adele's stack: kubernetes backend
on huburght, forge `git.fucken.ninja`; adele's `docs/gitea.md`). GitHub stays
canonical, and its hosted `builder-matrix` is the fallback.

The matrix runs **buddhafinger only** (Aaron, 2026-11-27), on Woodpecker and
in the hosted fallback alike: `MATRIX_PACKAGES` in
`projects/ritz/tools/builder_matrix.py`. The whole repo is still pushed to
Gitea. `list_packages()` still checks each listed package against the
eligibility rules (swept or opted in, no known `build`/`parity` failure)
and fails rather than emit an empty matrix. Widening the matrix again means
editing `MATRIX_PACKAGES` and regenerating the pipeline (below). Keeping
the CAS between runs is AGAST #4857 ("A persistent CAS", above).

On a push to main:

1. main.yml's `gitea-push` pushes the commit to `main` of
   `https://git.fucken.ninja/ritz-lang/rz.git` (Aaron, 2026-11-26: GitHub
   stays canonical and pushes; not a pull mirror, not `train.sh`). It runs
   `.github/scripts/push_to_gitea.sh` with the GitHub secret
   `GITEA_PUSH_TOKEN`. The script gives the token to git through a
   credential helper, never argv or the URL, and never forces. Runs queue in
   order (`concurrency: gitea-push`). Without the secret it warns, pushes
   nothing and says `pushed=false`; a rejected push fails the job.
2. `builder-fleet` runs `.github/scripts/woodpecker_fleet.py` only after a
   push that happened (`pushed=true`). It says `hosted=false` when
   `/api/healthz` answers, `ritz-lang/rz` is activated there, and no
   pipeline of it has been `pending` for `FALLBACK_SECONDS` (10 minutes;
   that means no agent is taking work). Anything else, including no push or
   a `workflow_dispatch` run, says `hosted=true`.
3. `builder-watch` makes the final call. When `builder-fleet` said
   Woodpecker, it runs `woodpecker_fleet.py --watch <commit>`, which polls
   the repo's pipelines anonymously every 20 s. It says `hosted=false` once
   this commit's pipeline has started, and `hosted=true` when the pipeline
   is still pending `FALLBACK_SECONDS` after it was created, never shows up,
   or ends without starting (killed, a config error). The probe alone can't
   see an agent that is missing before any pipeline is stuck: the first live
   push, `97eacd11d`, went to Woodpecker, sat `pending` with no agent for the
   `pool: rz-builder` label, and got no matrix anywhere. The watch also says
   `why`, which `builder-packages` prints as a notice.
4. `builder-image` computes this commit's content key ("Image versioning by
   content" above); if `:src-<key>` is already published it retags it as
   `:<commit>` (seconds), else it builds and tests the image (`test.sh`) and
   pushes `ghcr.io/ritz-lang/rz-builder:<commit>` and `:src-<key>`. It hands
   the image to the hosted matrix only when `builder-watch` says
   `hosted=true`.
5. `builder-packages` and `builder-matrix` run only when `builder-watch`
   says `hosted=true`, so GitHub spends no matrix minutes while the fleet is
   up.
6. The push's webhook (Gitea to Woodpecker) starts
   `.woodpecker/builder.yml`:
   - `wait-for-image` polls ghcr anonymously until `:<commit>` exists, for
     up to 40 minutes. A step whose pod can't pull its image fails at once.
   - Then comes one step per package, in the order `builder_matrix.py matrix`
     gives (today one step, `buddhafinger`). Each step is a pod whose image is
     `ghcr.io/ritz-lang/rz-builder:${CI_COMMIT_SHA}`, running
     `.github/scripts/woodpecker_builder_step.sh`. That script calls the
     entrypoint with `RZ_ROOT` set to the clone, then applies the same
     zero-test check as `run_builder_package.sh`
     (`check_builder_summary.py`).
   - Steps have no `depends_on`, so they run one at a time. Every package
     runs whatever the one before it did.
   - A pipeline that started more than `FALLBACK_SECONDS` + 5 minutes after
     it was created (`CI_PIPELINE_STARTED - CI_PIPELINE_CREATED`) is one
     `builder-watch` gave up on, and GitHub ran that commit. Every step
     skips in seconds and says so. Without a token GitHub can't cancel the
     pipelines it gave up on, so when an agent appears after an outage it
     clears that queue fast instead of spending ~15 minutes on each. The 5
     minutes of slack mean a pipeline starting near the deadline runs on
     both, never on neither.

The pipeline is generated, so don't edit it. When the matrix moves (a
change to `MATRIX_PACKAGES`), regenerate it:

```bash
python3 projects/ritz/tools/builder_matrix.py woodpecker --write
```

`tools/test_woodpecker_builder.py` fails while it is stale. It also pins the
cluster's rules:
- no privileged step, service or secret, and no volume but the package
  steps' `rz-builder-cas:/cache` (so no hostPath or docker.sock);
- uid 1000 (`runAsNonRoot`, no privilege escalation);
- an 8Gi memory limit and no CPU request or limit (adele's no-CPU-limits
  rule; without a request, a step gets the smallest CPU weight on the box,
  below train gates and rooms);
- no seccomp profile;
- `labels: pool: rz-builder`.

The seccomp profile matters if the matrix widens again. Under a
RuntimeDefault-style profile (Docker's default), the image of 31d73e00e
fails 19 of ritzlib's 896 tests, because they call io_uring. Pod Security `baseline` forbids naming `Unconfined`, so
the pods depend on the kubelet's default staying unset (no
`--seccomp-default`).

Checked locally on the image of 31d73e00e: each step command ran in the
image with its entrypoint replaced, as uid 1000, the clone as the working
directory, and no seccomp profile.

### Cluster side (adele's cluster, applied by adele)

**For now** (Aaron, 2026-11-27) rz runs on one of adele's shared agents,
which adele labelled `pool=rz-builder`. Its steps run in
`woodpecker-steps`, with no rz LimitRange or ResourceQuota; the memory
limit in each step is the only cap. Pipeline #1 (`97eacd11d`) went green
on it. The dedicated agent below is the plan if that changes:

- A public, empty Gitea repo `ritz-lang/rz` (no README or licence, so the
  first push, of GitHub's full history, is a fast-forward), with no branch
  protection on `main` that refuses the push account.
- An rz agent, `woodpecker-agent-rz`:
  - `WOODPECKER_AGENT_LABELS=pool=rz-builder` and `WOODPECKER_MAX_WORKFLOWS=1`;
  - its own steps namespace (Pod Security `baseline`, tokenless default
    ServiceAccount, the agent's Role only there);
  - a LimitRange (memory only) and a ResourceQuota.

  The existing agents and `woodpecker-steps` don't change.

### What only Aaron or adele can do

- Make the `rz-builder` package public on ghcr.io (package settings,
  "Change visibility"). Today an anonymous pull is refused (401), and step
  pods have no pull secret.
- The push token. Gitea has no repo-scoped deploy token, so: a Gitea
  account with write access to `ritz-lang/rz` only (a bot user is safest),
  and an access token of it with scope `write:repository`. Store it as the
  GitHub Actions repository secret `GITEA_PUSH_TOKEN` of `ritz-lang/rz`
  (`gh secret set GITEA_PUSH_TOKEN -R ritz-lang/rz`). Until then
  `gitea-push` warns and the hosted matrix runs.
- Activate `ritz-lang/rz` in Woodpecker (Gitea OAuth login as an owner of
  the repo; that adds the push webhook), and set it public, so
  `woodpecker_fleet.py` can read it anonymously.
- None of these puts a token in this repo.

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
compiler. `stage_tree.PYTHON_FILES` lists the 35 files: `rz`, nine
`projects/ritz/*.py` modules, `tools/known_failures.py`, and 24 ritz0
modules. Nothing outside the standard library is imported.

The standard library modules include `tomllib`, `shutil`, `tempfile`,
`concurrent.futures`, `uuid`, `lzma` and `bz2`. Debian's `python3-minimal`
lacks those, so the runtime installs `python3-minimal` plus
`libpython3.13-stdlib` (Python 3.13; rz needs ≥ 3.11 for `tomllib`).

A build never imports pytest, but a package's `test.sh` may: rllvm's and
razm's run `python3 -m pytest` (AGAST #4847). The bootstrap stage installs
CI's pinned pytest (`requirements.lock`) and its pure-Python dependencies
with `pip --target`, and the runtime copies them into
`/usr/lib/python3/dist-packages`. The image has no pip and no venv.

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
| `nm`, `objdump` (binutils), pytest | rllvm's `test.sh` (pytest) | its oracle checks: symbol tables and disassembly (AGAST #4847) |

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
