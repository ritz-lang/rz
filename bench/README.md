# bench/ — End-to-end performance harness

Benchmarks the full `valet → zeus → nexus → mausoleum` stack and prints
a Markdown matrix.  Designed so you can re-run it after every change
and watch the numbers move.

## Quick start

```sh
# Default matrix (debug builds, 10s wrk, 4 threads, 100 conns, zeus -w 1)
./bench/run.sh

# Tighter numbers / longer run
./bench/run.sh --duration 30 --conns 200

# Test multi-worker scaling
./bench/run.sh --workers 4

# Skip the mausoleum-backed scenario (no DB process)
./bench/run.sh --skip mausoleum

# Emit machine-readable JSON alongside the table
./bench/run.sh --json /tmp/bench.json

# Leave servers running after the run (for poking at by hand)
./bench/run.sh --keep
```

## What it measures

| # | Path | What it tells you |
|---|---|---|
| **A** | Valet direct, `GET /` (Hello, World!) | HTTP perf ceiling — no zeus, no app logic |
| **B** | Valet direct, `GET /json` | Same as A but with a small JSON body |
| **C** | Valet direct, `GET /static/test.html` (1.4 KB) | File-system read cost per request (no `sendfile`) |
| **D** | Valet → zeus → nexus, `GET /` | Cost of going through the proxy + IPC ring + nexus dispatch |
| **E** | Valet → zeus → nexus, `GET /wiki/welcome` | Same path with a real route + page render |
| **F** | Valet → zeus → nexus → mausoleum (serial), `/wiki/welcome` | Adds the persistent DB roundtrip |

After [the futex wakeup wedge](../docs/), the remaining bottleneck on
the proxy scenarios (D/E/F) is **valet's main task blocking
in-kernel during the IPC roundtrip** — `zeus -w 4` doesn't move the
needle until that is fixed.

## Reproducibility notes

- All scenarios run on `127.0.0.1` so kernel TCP doesn't touch a NIC.
- Each scenario is a separate listener on its own port and each proxy
  uses its own Unix socket.  No scenario leaks load into another.  Ports
  are free ones picked at start (pin them with `BENCH_PORT_DIRECT`,
  `BENCH_PORT_STATIC`, `BENCH_PORT_PROXY`, `BENCH_PORT_PROXY_DB`,
  `BENCH_PORT_MAUSOLEUM`), so rooms benching on one host never collide.
- The static asset is `bench/static/test.html` — committed at exactly
  1386 bytes so the throughput → MB/sec column is comparable across
  runs.
- Configs are templates committed alongside.  `valet-static.json`
  contains a `BENCH_STATIC_ROOT` placeholder which `run.sh` substitutes
  with the absolute path at runtime; the rendered file is written next
  to the original with a `.rendered.json` suffix so you can inspect it.
- The script refuses to start while this worktree's own valet / nexus /
  zeus / mausoleum binaries are still running (matched on
  `/proc/PID/exe`, so other worktrees' servers don't count), and on
  `EXIT` kills only the processes it started and their children (unless
  `--keep` is passed).  `--dry-run` prints the ports, the orphan check
  and what cleanup would kill, and starts nothing.
- Sockets, the mausoleum data dir and logs live in one `mktemp -d`
  scratch dir, removed on `EXIT`, so concurrent runs on one host never
  share a path.  To inspect logs, pass `--keep`: the dir is left and its
  path printed.  If a scenario looks wrong, check `logs/v-direct.log`,
  `v-static.log`, `z-inmem.log`, `z-db.log`, `m-serial.log`, etc.

## Why these scenarios in this order

The matrix climbs from "what's the floor of the HTTP server itself" to
"what does the full DB-backed wiki cost".  Each step adds exactly one
piece of the production stack:

```
A → B    +JSON body
A → C    +disk read
A → D    +zeus IPC +nexus
D → E    +real route handler
E → F    +mausoleum TCP +DB GET
```

That's why a regression on F that doesn't show up on E points at
mausoleum (the only thing that changed).  Don't add scenarios that
mix two new factors at once — you'll lose the diagnostic clarity.

---

# Compile-time harness: `bench/compile.sh`

`run.sh` measures what the stack does at runtime; `compile.sh` measures
what it costs to build, under each of the three compilers: **ritz0**
(Python bootstrap), **ritz1** (built by ritz0) and **ritz1_selfhosted**
(ritz1 built by itself).

```sh
# Every compiler, the default projects (zeus rzrz tome valet mausoleum nexus)
./bench/compile.sh

# ritz0 vs ritz1 only, three samples each, JSON alongside the table
./bench/compile.sh --compiler ritz0,ritz1 --repeat 3 --json /tmp/compile.json

# Two projects, without timing the ritz1 rebuild and bootstrap
./bench/compile.sh --projects valet,zeus --skip-self-build

# Print the plan without building anything
./bench/compile.sh --dry-run
```

## What it measures

| Measurement | How |
|---|---|
| ritz1 from clean | `make -C projects/ritz/ritz1 distclean`, then `make … ritz1` timed |
| Bootstrap | `rm -f build/*_sh.ll build/*_sh.o build/ritz1_selfhosted`, then `make … bootstrap` timed. The ritz0-built `ritzlib_*.o` stay: `ritz1_selfhosted` links them |
| Cold build, per compiler × project | project `build/` and `.ritz-cache*` removed, project modules pruned from the artifact store, `./rz build P --compiler C` timed |
| Warm rebuild | the same build again with nothing changed |
| `--help` smoke | the package's binary (the `[[bin]]` named after the package, else the first) run with `--help` under a timeout: `ok`, `exit N`, `timeout` or `crash (signal N)` |

The table reports the median of `--repeat N` samples and each compiler's
cold time relative to ritz0. Any failed sample shows `FAIL` and makes the
script exit 1, after the table and JSON are written. A `--help` result
other than `ok` is reported but doesn't fail the run: not every binary
has `--help` (tome's don't).

## What "cold" means

Cold is cold for the **project**, not for ritzlib, which matches a real
dev cycle: ritzlib is already compiled; your project and its project
dependencies aren't.

- Compiled modules live in the content-addressed artifact store
  (`projects/ritz/cas.py`), not in `build/` or `.ritz-cache*`. Purging
  those two alone would still leave every object a store hit, so the
  build would be warm.
- The run uses a private store (`RITZ_CACHE_DIR` in its `mktemp -d`). The
  shared `~/.cache/ritz/cas` is never read or written, so another room's
  entries can't warm a cold build and this run can't evict theirs.
- Each compiler first builds every project once, untimed, to prime
  ritzlib. Before each cold sample, every store object whose `meta`
  record doesn't name a `projects/ritz/ritzlib/` module is deleted.

Because the store starts empty, the first run of the priming builds and
the ritz1 rebuild compile ritzlib from scratch. Expect several minutes
per compiler.

## Output

A Markdown table on stdout (progress goes to stderr). `--json FILE` also
writes:

- `settings`: compilers, projects, repeat, cold semantics.
- `provenance`: git HEAD, whether the tree was dirty, and sha256 of ritz0's
  Python sources and of the `ritz1` and `ritz1_selfhosted` binaries
  (`absent` if not built).
- `results`: one row per sample, with `phase` (`cold`, `warm`,
  `ritz1_clean` or `bootstrap`), `compiler`, `project` (`-` for the
  compiler builds), `sample`, `seconds`, `status` (`ok`, `fail` or
  `skipped`) and `smoke`.

Logs and the private store live in a scratch dir removed on exit. Pass
`--keep` to keep it; its path is printed. A failed build's last log lines
are printed to stderr either way.

Its tests are `projects/ritz/tools/test_bench_compile.py` (part of `make
tools-unit`), which run the script against a stub `rz` and stub ritz1
Makefile.
