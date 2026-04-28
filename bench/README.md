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
- Each scenario is a separate listener on its own port (9001–9004) and
  each proxy uses its own Unix socket (`/tmp/zeus_bench_*.sock`).  No
  scenario leaks load into another.
- The static asset is `bench/static/test.html` — committed at exactly
  1386 bytes so the throughput → MB/sec column is comparable across
  runs.
- Configs are templates committed alongside.  `valet-static.json`
  contains a `BENCH_STATIC_ROOT` placeholder which `run.sh` substitutes
  with the absolute path at runtime; the rendered file is written next
  to the original with a `.rendered.json` suffix so you can inspect it.
- The script kills any lingering debug binaries from previous runs
  before starting and on `EXIT` (unless `--keep` is passed).
- Logs land in `/tmp/bench-logs/`.  If a scenario looks wrong, check
  `v-direct.log`, `v-static.log`, `z-inmem.log`, `z-db.log`,
  `m-serial.log`, etc.

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
