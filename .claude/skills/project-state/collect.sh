#!/usr/bin/env bash
# collect.sh — measure the Ritz stack's state of the nation, emit one JSON doc.
#
# Read-only: the only write is `git fetch` (skip it with --no-fetch). Every
# number the project-state skill shows must come from this output or from the
# AGAST roll-up described in SKILL.md, never from memory.
#
# Usage:  .claude/skills/project-state/collect.sh [--no-fetch] [--runs N] > state.json
#   --runs N   how many main-branch CI runs to scan for "last green" per job (default 15)
#
# Needs: git, python3 (3.11+, tomllib), gh (optional: CI section is empty without it),
#        systemctl --user (optional: rooms section is empty without it).
set -euo pipefail

FETCH=1
RUNS=15
while [ $# -gt 0 ]; do
    case "$1" in
        --no-fetch) FETCH=0 ;;
        --runs) RUNS="$2"; shift ;;
        -h|--help) sed -n 2,13p "$0"; exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
    shift
done

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cd "$ROOT"
[ "$FETCH" = 1 ] && git fetch -q origin main

RUNS="$RUNS" python3 -I - <<'PY'
import collections, datetime as dt, json, os, re, subprocess, sys, tomllib

REF = "origin/main"
RUNS = int(os.environ["RUNS"])


def sh(*cmd, check=True):
    """Run a command, return stdout ('' if the tool is missing and check=False)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return r.stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        if check:
            raise
        return ""


# ---------------------------------------------------------------------------
# Layer map: the ONE place packages are assigned to layers. SKILL.md refers
# here. Any project under projects/ that is not listed lands in "unmapped",
# so a new package shows up instead of silently vanishing from the report.
# ---------------------------------------------------------------------------
LAYERS = {
    "1 · Compiler": ["ritz", "ritzlib", "ritzunit", "ritz-lsp", "rzrz"],
    "2 · Kernel": ["harland"],
    "3 · OS / userland": ["indium", "rzsh", "ritzutils"],
    "4 · Desktop": ["prism", "angelo", "angelo-simple", "iris"],
    "5 · Productivity": ["tempest", "lexis", "sage", "nexus", "spectree"],
    "Foundation · Server & infra": ["valet", "zeus", "spire", "http", "cryptosec",
                                    "squeeze", "mausoleum", "tome", "goliath"],
    "Not a layer (reviews/docs)": ["larb"],
}
# Paths that are tracked but are not live code (rz.toml [workspace.exclude]).
DEAD_PREFIXES = ("projects/ritz/docs/archive/",)
# The regression corpus: real Ritz, but test inputs, not the compiler. Counted
# separately (examples_kloc) so the compiler layer's kLOC is the compiler.
CORPUS_PREFIX = "projects/ritz/examples/"
# Sub-trees of projects/ritz worth naming in the compiler row.
RITZ_PARTS = {"ritz1": "projects/ritz/ritz1/", "ritzlib": "projects/ritz/ritzlib/"}

head = sh("git", "rev-parse", REF).strip()
head_subject = sh("git", "log", "-1", "--format=%s", REF).strip()
now = dt.datetime.now(dt.timezone.utc)

# --- lines of code per project (tracked files at origin/main) ---------------
files = sh("git", "ls-tree", "-r", "--name-only", REF).splitlines()
ritz_lines = collections.Counter()   # project -> live .ritz lines
part_lines = collections.Counter()   # RITZ_PARTS key -> .ritz lines
py_lines = collections.Counter()     # "ritz0" (the compiler M1.4 retires) / "tooling"
examples_lines = 0


def nlines(path):
    try:
        with open(path, "rb") as fh:
            return fh.read().count(b"\n")
    except FileNotFoundError:   # in origin/main but not this worktree
        return 0


for f in files:
    if not f.startswith("projects/") or f.startswith(DEAD_PREFIXES):
        continue
    proj = f.split("/")[1]
    if f.endswith(".ritz"):
        if f.startswith(CORPUS_PREFIX):
            examples_lines += nlines(f)
            continue
        n = nlines(f)
        ritz_lines[proj] += n
        for part, prefix in RITZ_PARTS.items():
            if f.startswith(prefix):
                part_lines[part] += n
    elif f.endswith(".py") and proj == "ritz":
        py_lines["ritz0" if f.startswith("projects/ritz/ritz0/") else "tooling"] += nlines(f)

projects = sorted(d for d in os.listdir("projects")
                  if os.path.isdir(f"projects/{d}") and not d.startswith("."))
mapped = {p for ps in LAYERS.values() for p in ps}
layers = []
for name, pkgs in LAYERS.items():
    layers.append({
        "layer": name,
        "packages": pkgs,
        "ritz_kloc": round(sum(ritz_lines[p] for p in pkgs) / 1000, 1),
        "per_package_kloc": {p: round(ritz_lines[p] / 1000, 1) for p in pkgs},
    })
unmapped = [p for p in projects if p not in mapped]


# --- known failures (the allowlists ARE the roadmap, ROADMAP.md §46) --------
def list_entries(path):
    try:
        with open(path) as fh:
            return [l.strip() for l in fh if l.strip() and not l.lstrip().startswith("#")]
    except FileNotFoundError:
        return None

kf0 = list_entries("projects/ritz/scripts/regression-known-failures.txt")
kf1 = list_entries("projects/ritz/scripts/regression-known-failures-ritz1.txt")

matrix = {}
try:
    sys.path.insert(0, "projects/ritz/tools")
    import run_regression_matrix as m  # noqa: E402  (repo code, data only)
    matrix = dict(collections.Counter(k[0] for k in m.EXPECTED_FAILURES))
except Exception as e:  # report, don't guess
    matrix = {"error": f"{type(e).__name__}: {e}"}

with open("rz.toml", "rb") as fh:
    rz = tomllib.load(fh)
build_excuses = {k: (re.findall(r"#\d+", v) or ["?"])[0]
                 for k, v in rz.get("ci", {}).get("known_failing", {}).get("build", {}).items()}

# --- pace: commits and ticket branches merged, per month --------------------
pace = collections.OrderedDict()
ticket_re = re.compile(r"^ritz-task-\d+:")
log = sh("git", "log", REF, "--since=2026-01-01", "--format=%cI%x09%s").splitlines()
last7 = today = 0
for line in log:
    when, _, subj = line.partition("\t")
    t = dt.datetime.fromisoformat(when)
    key = t.strftime("%Y-%m")
    row = pace.setdefault(key, {"commits": 0, "tickets": 0})
    row["commits"] += 1
    if ticket_re.match(subj):
        row["tickets"] += 1
        if now - t <= dt.timedelta(days=7):
            last7 += 1
        if t.astimezone(dt.timezone.utc).date() == now.date():
            today += 1
pace = dict(sorted(pace.items()))
tickets_total = sum(1 for l in sh("git", "log", REF, "--format=%s").splitlines() if ticket_re.match(l))

# --- CI: latest conclusion and last green per job on main ------------------
ci = {"available": False}
runs_raw = sh("gh", "run", "list", "-b", "main", "-L", str(RUNS),
              "--json", "databaseId,headSha,conclusion,status,createdAt,workflowName", check=False)
if runs_raw.strip():
    runs = json.loads(runs_raw)
    jobs = {}   # job name -> {"latest":..., "last_green": {...}}
    for r in runs:  # newest first
        jr = sh("gh", "run", "view", str(r["databaseId"]), "--json", "jobs", check=False)
        if not jr.strip():
            continue
        for j in json.loads(jr)["jobs"]:
            e = jobs.setdefault(j["name"], {"latest": None, "latest_sha": None, "last_green": None})
            if e["latest"] is None:
                e["latest"] = j["conclusion"] or j["status"]
                e["latest_sha"] = r["headSha"][:7]
            if e["last_green"] is None and j["conclusion"] == "success":
                e["last_green"] = {"sha": r["headSha"][:7], "at": r["createdAt"]}
    ci = {
        "available": True,
        "runs_scanned": len(runs),
        "latest_run": {k: runs[0][k] for k in ("headSha", "status", "conclusion", "createdAt")} if runs else None,
        "head_has_run": any(r["headSha"] == head for r in runs),
        "jobs": jobs,
    }

# --- kernel boot gate: does any CI job boot an image? ----------------------
boot_gate_files = sh("git", "grep", "-liE", "qemu-system|ovmf", REF, "--", ".github", check=False)
boot_gate = [l.split(":", 1)[1] for l in boot_gate_files.splitlines()]

# --- live rooms -------------------------------------------------------------
units = sh("systemctl", "--user", "list-units", "--type=service", "--state=active",
           "--no-legend", "--plain", "adele-agent@ritz-task-*", check=False)
rooms = sorted(re.findall(r"adele-agent@(ritz-task-\d+)\.service", units))

state = {
    "measured_at": now.strftime("%Y-%m-%d %H:%M UTC"),
    "main": {"sha": head[:7], "subject": head_subject},
    "layers": layers,
    "unmapped_projects": unmapped,
    "ritz_parts_kloc": {k: round(v / 1000, 1) for k, v in part_lines.items()},
    "examples_kloc": round(examples_lines / 1000, 1),
    "python_kloc": {k: round(v / 1000, 1) for k, v in py_lines.items()},
    "known_failures": {
        "ritz0_regression": len(kf0) if kf0 is not None else None,
        "ritz1_regression": len(kf1) if kf1 is not None else None,
        "ritz1_regression_entries": kf1,
        "matrix_expected_by_compiler": matrix,
        "build_excused": build_excuses,
    },
    "pace": {"by_month": pace, "tickets_last_7d": last7, "tickets_today": today,
             "tickets_total": tickets_total},
    "ci": ci,
    "kernel": {"boot_gate_ci_files": boot_gate,
               "lld_link_on_host": bool(sh("sh", "-c", "command -v lld-link", check=False).strip())},
    "rooms_live": rooms,
}
json.dump(state, sys.stdout, indent=2)
print()
PY
