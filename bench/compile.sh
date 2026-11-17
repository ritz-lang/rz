#!/usr/bin/env bash
# bench/compile.sh — Compile-time benchmark harness: ritz0 vs ritz1 vs
# ritz1_selfhosted, building real workspace projects.
#
# The compile-time counterpart of bench/run.sh (runtime throughput).  For
# each compiler and project it times a cold build, a warm rebuild and runs
# the produced binary's --help as a smoke test.  Separately it times ritz1
# rebuilt from clean and the bootstrap (ritz1 compiling itself).  Prints a
# Markdown table; --json also writes the raw samples.
#
# Usage:
#   bench/compile.sh                               # all compilers, default projects
#   bench/compile.sh --compiler ritz0,ritz1        # comma list of compilers
#   bench/compile.sh --projects valet,zeus         # comma list of projects
#   bench/compile.sh --repeat 3                    # samples per measurement
#   bench/compile.sh --skip-self-build             # don't time ritz1 / bootstrap
#   bench/compile.sh --json /tmp/c.json            # also emit machine-readable JSON
#   bench/compile.sh --smoke-timeout 10            # seconds for each `BIN --help`
#   bench/compile.sh --keep                        # keep the scratch dir (logs, CAS)
#   bench/compile.sh --dry-run                     # print the plan, build nothing
#
# Compilers: ritz0, ritz1, ritz1_selfhosted (default: all three).
# Projects default to: zeus rzrz tome valet mausoleum nexus.
#
# Cold means cold for the PROJECT, not for ritzlib.  Builds use a private
# artifact store (RITZ_CACHE_DIR in a mktemp dir; the shared one in
# ~/.cache/ritz/cas is never read or written, so other rooms' entries
# can't make a cold build warm and this run can't evict theirs).  Before
# measuring, every project is built once per compiler to prime ritzlib;
# before each cold build every non-ritzlib entry is pruned from the store
# and the project's build/ and .ritz-cache* are removed.  That is the
# everyday developer cold build: ritzlib is already compiled, your project
# and its project dependencies are not.  Warm is an immediate rebuild with
# no changes.
#
# Exit status: 0 if every build succeeded, 1 if any failed (the table and
# JSON are still written), 2 on bad arguments.  --help smoke results are
# reported but don't affect the exit status: not every binary has --help.
#
# Requires: bash 5, python3, make, timeout, sha256sum, git, and what
# `./rz build` and `make -C projects/ritz/ritz1` need.

set -euo pipefail
export LC_ALL=C   # EPOCHREALTIME must use '.' as its radix

# ────────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────────

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PROJECTS_DIR="$REPO_ROOT/projects"
RITZ_DIR="$PROJECTS_DIR/ritz"
RITZ1_DIR="$RITZ_DIR/ritz1"
RZ="$REPO_ROOT/rz"

ALL_COMPILERS=(ritz0 ritz1 ritz1_selfhosted)
COMPILERS_ARG="ritz0,ritz1,ritz1_selfhosted"
PROJECTS_ARG="zeus,rzrz,tome,valet,mausoleum,nexus"
REPEAT=1
JSON_OUT=""
SKIP_SELF=0
SMOKE_TIMEOUT=10
KEEP=0
DRY_RUN=0

usage() { sed -n '/^# Usage:/,/^# Requires:/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }
die_usage() { echo "[compile] $*" >&2; exit 2; }

# ────────────────────────────────────────────────────────────────────
# Arg parsing
# ────────────────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --compiler|--compilers) COMPILERS_ARG="${2:?--compiler needs a value}"; shift 2 ;;
        --projects)       PROJECTS_ARG="${2:?--projects needs a value}";  shift 2 ;;
        --repeat)         REPEAT="${2:?--repeat needs a value}";          shift 2 ;;
        --json)           JSON_OUT="${2:?--json needs a file}";           shift 2 ;;
        --smoke-timeout)  SMOKE_TIMEOUT="${2:?--smoke-timeout needs a value}"; shift 2 ;;
        --skip-self-build) SKIP_SELF=1; shift ;;
        --keep)           KEEP=1;       shift ;;
        --dry-run)        DRY_RUN=1;    shift ;;
        -h|--help)        usage; exit 0 ;;
        *) die_usage "unknown arg: $1 (see --help)" ;;
    esac
done

IFS=', ' read -r -a COMPILERS <<< "$COMPILERS_ARG"
IFS=', ' read -r -a PROJECTS <<< "$PROJECTS_ARG"
[[ ${#COMPILERS[@]} -gt 0 ]] || die_usage "--compiler: empty list"
[[ ${#PROJECTS[@]} -gt 0 ]]  || die_usage "--projects: empty list"
for c in "${COMPILERS[@]}"; do
    [[ " ${ALL_COMPILERS[*]} " == *" $c "* ]] \
        || die_usage "--compiler: unknown compiler '$c' (choose from ${ALL_COMPILERS[*]})"
done
[[ "$REPEAT" =~ ^[1-9][0-9]*$ ]] || die_usage "--repeat must be a positive integer, got '$REPEAT'"
[[ "$SMOKE_TIMEOUT" =~ ^[1-9][0-9]*$ ]] \
    || die_usage "--smoke-timeout must be a positive integer, got '$SMOKE_TIMEOUT'"

wants() { [[ " ${COMPILERS[*]} " == *" $1 "* ]]; }

if [[ "$DRY_RUN" == "1" ]]; then
    echo "[compile] dry-run: compilers: ${COMPILERS[*]}" >&2
    echo "[compile] dry-run: projects: ${PROJECTS[*]}" >&2
    echo "[compile] dry-run: repeat: $REPEAT, self-build timing: $([[ $SKIP_SELF == 1 ]] && echo no || echo yes)" >&2
    exit 0
fi

for p in "${PROJECTS[@]}"; do
    [[ -f "$PROJECTS_DIR/$p/ritz.toml" ]] || die_usage "--projects: no project '$p' ($PROJECTS_DIR/$p/ritz.toml)"
done

# ────────────────────────────────────────────────────────────────────
# Scratch dir: logs, results and the private artifact store
# ────────────────────────────────────────────────────────────────────

T=$(mktemp -d)
# shellcheck disable=SC2329  # invoked by the EXIT trap below
cleanup() {
    if [[ "$KEEP" == "1" ]]; then
        echo "[compile] --keep: logs and artifact store left in $T" >&2
    else
        rm -rf "$T"
    fi
}
trap cleanup EXIT

LOG_DIR="$T/logs"
RESULTS="$T/results.tsv"
mkdir -p "$LOG_DIR"
: > "$RESULTS"
export RITZ_CACHE_DIR="$T/cas"
FAILED=0

# ────────────────────────────────────────────────────────────────────
# Utilities
# ────────────────────────────────────────────────────────────────────

# timed LOG CMD...: run CMD with all output to LOG (a file, not a pipe:
# `cmd | tee` would report tee's status), set ELAPSED to wall seconds and
# return CMD's exit status.
ELAPSED=0
timed() {
    local log="$1"; shift
    local t0 t1 rc=0
    t0=$EPOCHREALTIME
    "$@" >"$log" 2>&1 || rc=$?
    t1=$EPOCHREALTIME
    ELAPSED=$(awk -v a="$t0" -v b="$t1" 'BEGIN { printf "%.3f", b - a }')
    return "$rc"
}

# record PHASE COMPILER PROJECT SAMPLE SECONDS STATUS SMOKE
record() {
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$@" >> "$RESULTS"
}

# fail_note WHAT LOG: report a failed build with the tail of its log.
fail_note() {
    FAILED=1
    echo "[compile] FAIL: $1 — last lines of its log:" >&2
    tail -n 15 "$2" | sed 's/^/[compile]   /' >&2
}

# Remove every artifact-store object that is not a ritzlib module, so the
# next build compiles the project and its project dependencies from source
# while ritzlib stays primed.  Object-driven: an object with no meta record
# is not known to be ritzlib, so it goes too.
prune_store() {
    python3 - "$RITZ_CACHE_DIR" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
for obj in list(root.glob("objects/*/*")):
    if obj.suffix not in (".ll", ".o"):
        continue                      # keymemos and lock files
    meta = root / "meta" / obj.stem[:2] / f"{obj.stem}.json"
    try:
        module = json.loads(meta.read_text()).get("module", "")
    except (OSError, ValueError):
        module = ""
    if not module.startswith("projects/ritz/ritzlib/"):
        obj.unlink(missing_ok=True)
        meta.unlink(missing_ok=True)
PY
}

purge_project() {
    rm -rf "${PROJECTS_DIR:?}/$1/build"
    local d
    for d in "$PROJECTS_DIR/$1"/.ritz-cache*; do
        [[ -e "$d" ]] && rm -rf "$d"
    done
    return 0
}

# The binary to smoke-test: the [[bin]] named after the package, else the
# first [[bin]].  Empty if the project declares none.
smoke_bin() {
    python3 - "$PROJECTS_DIR/$1/ritz.toml" <<'PY'
import sys, tomllib
with open(sys.argv[1], "rb") as f:
    data = tomllib.load(f)
bins = [b["name"] for b in data.get("bin", []) if "name" in b]
name = data.get("package", {}).get("name")
print(name if name in bins else (bins[0] if bins else ""))
PY
}

# smoke PROJECT: run its binary's --help; echo ok / exit N / timeout /
# crash (signal N) / missing / none.
smoke() {
    local bin path rc=0
    bin=$(smoke_bin "$1")
    [[ -n "$bin" ]] || { echo none; return; }
    path="$PROJECTS_DIR/$1/build/debug/$bin"
    [[ -x "$path" ]] || { echo missing; return; }
    timeout -k 2 "$SMOKE_TIMEOUT" "$path" --help </dev/null >"$LOG_DIR/smoke-$1.log" 2>&1 || rc=$?
    case "$rc" in
        0)   echo ok ;;
        124) echo timeout ;;
        137) echo timeout ;;      # killed by timeout -k
        *)   if (( rc > 128 )); then echo "crash (signal $((rc - 128)))"; else echo "exit $rc"; fi ;;
    esac
}

make_ritz1() { make -C "$RITZ1_DIR" "$@"; }

# ────────────────────────────────────────────────────────────────────
# 1. ritz1 from clean and the bootstrap
# ────────────────────────────────────────────────────────────────────

self_build_timing() {
    echo "[compile] priming ritzlib for the ritz1 build" >&2
    if ! make_ritz1 ritz1 >"$LOG_DIR/ritz1-prime.log" 2>&1; then
        fail_note "make -C ritz1 ritz1 (prime)" "$LOG_DIR/ritz1-prime.log"
        record ritz1_clean ritz0 - 1 "" fail -
        return
    fi
    local s log
    for ((s = 1; s <= REPEAT; s++)); do
        echo "[compile] ritz1 from clean, sample $s/$REPEAT" >&2
        make_ritz1 distclean >"$LOG_DIR/ritz1-distclean.log" 2>&1
        log="$LOG_DIR/ritz1-clean-$s.log"
        if timed "$log" make_ritz1 ritz1; then
            record ritz1_clean ritz0 - "$s" "$ELAPSED" ok -
        else
            record ritz1_clean ritz0 - "$s" "$ELAPSED" fail -
            fail_note "ritz1 from clean" "$log"
            return
        fi
    done
    for ((s = 1; s <= REPEAT; s++)); do
        echo "[compile] bootstrap, sample $s/$REPEAT" >&2
        # Only the self-hosted outputs.  The ritzlib_*.o are ritz0-built,
        # shared with ritz1, and linked into ritz1_selfhosted as-is.
        rm -f "$RITZ1_DIR"/build/*_sh.ll "$RITZ1_DIR"/build/*_sh.o "$RITZ1_DIR/build/ritz1_selfhosted"
        log="$LOG_DIR/bootstrap-$s.log"
        if timed "$log" make_ritz1 bootstrap; then
            record bootstrap ritz1 - "$s" "$ELAPSED" ok -
        else
            record bootstrap ritz1 - "$s" "$ELAPSED" fail -
            fail_note "make -C ritz1 bootstrap" "$log"
            return
        fi
    done
}

if [[ "$SKIP_SELF" == "0" ]]; then
    self_build_timing
fi

# Whatever was or wasn't timed, the swept ritz1-family compilers must be
# current.  Make is incremental, so this is cheap when they already are.
if wants ritz1 || wants ritz1_selfhosted; then
    make_ritz1 ritz1 >"$LOG_DIR/ensure-ritz1.log" 2>&1 \
        || fail_note "make -C ritz1 ritz1" "$LOG_DIR/ensure-ritz1.log"
fi
if wants ritz1_selfhosted; then
    make_ritz1 bootstrap >"$LOG_DIR/ensure-bootstrap.log" 2>&1 \
        || fail_note "make -C ritz1 bootstrap" "$LOG_DIR/ensure-bootstrap.log"
fi

# ────────────────────────────────────────────────────────────────────
# 2. Provenance
# ────────────────────────────────────────────────────────────────────

GIT_HEAD=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)
GIT_DIRTY=false
[[ -n "$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null)" ]] && GIT_DIRTY=true

hash_file() { if [[ -f "$1" ]]; then sha256sum "$1" | cut -d' ' -f1; else echo absent; fi; }
# ritz0 is a Python tree: hash every .py file's path and content.
HASH_RITZ0=$(cd "$RITZ_DIR" && find ritz0 -name '*.py' -type f | sort | xargs -r sha256sum | sha256sum | cut -d' ' -f1)
HASH_RITZ1=$(hash_file "$RITZ1_DIR/build/ritz1")
HASH_RITZ1_SH=$(hash_file "$RITZ1_DIR/build/ritz1_selfhosted")

# ────────────────────────────────────────────────────────────────────
# 3. The compiler × project sweep
# ────────────────────────────────────────────────────────────────────

for c in "${COMPILERS[@]}"; do
    echo "[compile] $c: priming ritzlib (one untimed build per project)" >&2
    for p in "${PROJECTS[@]}"; do
        "$RZ" build "$p" --compiler "$c" >"$LOG_DIR/prime-$c-$p.log" 2>&1 || true
    done
    for ((s = 1; s <= REPEAT; s++)); do
        for p in "${PROJECTS[@]}"; do
            echo "[compile] $c: $p, sample $s/$REPEAT" >&2
            purge_project "$p"
            prune_store
            log="$LOG_DIR/cold-$c-$p-$s.log"
            if timed "$log" "$RZ" build "$p" --compiler "$c"; then
                record cold "$c" "$p" "$s" "$ELAPSED" ok "$(smoke "$p")"
            else
                record cold "$c" "$p" "$s" "$ELAPSED" fail -
                record warm "$c" "$p" "$s" "" skipped -
                fail_note "$c cold build of $p" "$log"
                continue
            fi
            log="$LOG_DIR/warm-$c-$p-$s.log"
            if timed "$log" "$RZ" build "$p" --compiler "$c"; then
                record warm "$c" "$p" "$s" "$ELAPSED" ok -
            else
                record warm "$c" "$p" "$s" "$ELAPSED" fail -
                fail_note "$c warm rebuild of $p" "$log"
            fi
        done
    done
done

# ────────────────────────────────────────────────────────────────────
# 4. Markdown table (stdout) and JSON
# ────────────────────────────────────────────────────────────────────

CB_COMPILERS="${COMPILERS[*]}" CB_PROJECTS="${PROJECTS[*]}" CB_REPEAT="$REPEAT" \
CB_SELF="$SKIP_SELF" CB_SMOKE_TIMEOUT="$SMOKE_TIMEOUT" CB_HEAD="$GIT_HEAD" CB_DIRTY="$GIT_DIRTY" \
CB_H0="$HASH_RITZ0" CB_H1="$HASH_RITZ1" CB_H1SH="$HASH_RITZ1_SH" \
python3 - "$RESULTS" "$JSON_OUT" <<'PY'
import json, os, statistics, sys

E = os.environ
results_path, json_out = sys.argv[1], sys.argv[2]
compilers = E["CB_COMPILERS"].split()
projects = E["CB_PROJECTS"].split()
settings = {
    "compilers": compilers,
    "projects": projects,
    "repeat": int(E["CB_REPEAT"]),
    "self_build_timed": E["CB_SELF"] == "0",
    "smoke_timeout_secs": int(E["CB_SMOKE_TIMEOUT"]),
    "cold": "private artifact store; ritzlib primed, project modules, build/ and .ritz-cache* purged",
}
provenance = {
    "git_head": E["CB_HEAD"],
    "git_dirty": E["CB_DIRTY"] == "true",
    "compilers": {"ritz0": E["CB_H0"], "ritz1": E["CB_H1"],
                  "ritz1_selfhosted": E["CB_H1SH"]},
}

rows = []
with open(results_path) as f:
    for line in f:
        phase, comp, proj, sample, secs, status, smoke = line.rstrip("\n").split("\t")
        rows.append({"phase": phase, "compiler": comp, "project": proj,
                     "sample": int(sample), "seconds": float(secs) if secs else None,
                     "status": status, "smoke": smoke})

def cell(phase, comp, proj):
    """Median seconds over the samples, or FAIL if any sample failed."""
    sel = [r for r in rows if (r["phase"], r["compiler"], r["project"]) == (phase, comp, proj)]
    if not sel:
        return None, "-"
    if any(r["status"] != "ok" for r in sel):
        return None, "FAIL"
    med = statistics.median(r["seconds"] for r in sel)
    return med, f"{med:.2f}"

head = provenance["git_head"][:12] + (" (dirty)" if provenance["git_dirty"] else "")
print()
print(f"## Compile-time benchmark — {', '.join(compilers)}; "
      f"median of {settings['repeat']} sample(s); HEAD {head}")
print()
print("| Project | Compiler | Cold (s) | Warm (s) | Cold ×ritz0 | `--help` |")
print("|---|---|---:|---:|---:|---|")
for proj in projects:
    base, _ = cell("cold", "ritz0", proj)
    for comp in compilers:
        cold, cold_s = cell("cold", comp, proj)
        _, warm_s = cell("warm", comp, proj)
        ratio = f"{cold / base:.2f}" if cold is not None and base else "-"
        smokes = sorted({r["smoke"] for r in rows
                         if (r["phase"], r["compiler"], r["project"]) == ("cold", comp, proj)
                         and r["smoke"] != "-"})
        print(f"| {proj} | {comp} | {cold_s} | {warm_s} | {ratio} | {', '.join(smokes) or '-'} |")

if settings["self_build_timed"]:
    print()
    print("| Compiler build | Time (s) |")
    print("|---|---:|")
    print(f"| ritz1 from clean (ritz0 compiles ritz1) | {cell('ritz1_clean', 'ritz0', '-')[1]} |")
    print(f"| bootstrap (ritz1 compiles ritz1_selfhosted) | {cell('bootstrap', 'ritz1', '-')[1]} |")

print()
for name, h in provenance["compilers"].items():
    print(f"- {name}: `{h[:16]}`")

if json_out:
    with open(json_out, "w") as f:
        json.dump({"settings": settings, "provenance": provenance, "results": rows}, f, indent=2)
        f.write("\n")
    print(f"[compile] JSON written to {json_out}", file=sys.stderr)
PY

exit "$FAILED"
