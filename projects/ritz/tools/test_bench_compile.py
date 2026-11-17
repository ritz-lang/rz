"""bench/compile.sh: the compile-time counterpart of bench/run.sh (AGAST #1270).

It replaces two scratch scripts (`.bench-stack.sh`, `.bench-stack-v2.sh`)
whose numbers were wrong in ways that looked plausible:

  * v1 ran `make -C ritz1 ritz1_selfhosted`, a target that does not exist,
    and timed the failed make as "bootstrap";
  * v1 took `RC=$?` after `build | tee`, the exit status of tee, so a failed
    cold build was reported as a pass;
  * neither swept the compiler axis: v1 always built with ritz0, v2 always
    with ritz1, so the three-compiler comparison was never run.

Real builds take minutes, so these tests copy compile.sh into a fake repo
(it finds everything from BASH_SOURCE) with a stub `rz` and a stub
`ritz1/Makefile` that log what they were asked to do and what they saw on
disk when asked.  The CAS is real in shape (meta/<k[:2]>/<k>.json naming the
module, objects/<k[:2]>/<k>.o) so the "ritzlib stays primed, project modules
go cold" pruning is exercised as it runs against the real store.
"""

import json
import os
import shutil
import stat
import subprocess
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
COMPILE_SH = REPO / "bench" / "compile.sh"

# Stub `rz build <proj> --compiler <c>`: logs one JSON line describing the
# tree it found, then "builds" by writing the project's binary, its
# .ritz-cache dir and one ritzlib + one project entry into $RITZ_CACHE_DIR.
STUB_RZ = r"""#!/usr/bin/env bash
set -u
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ "$1" == build ]] || { echo "stub rz: unexpected $*" >&2; exit 2; }
proj="$2"; compiler=ritz0
[[ "${3:-}" == --compiler ]] && compiler="$4"
pdir="$root/projects/$proj"
cas="${RITZ_CACHE_DIR:?RITZ_CACHE_DIR unset}"
have() { [[ -e "$1" ]] && echo true || echo false; }
caches=false; compgen -G "$pdir/.ritz-cache*" >/dev/null && caches=true
printf '{"proj":"%s","compiler":"%s","build":%s,"ritz_cache":%s,"cas_ritzlib":%s,"cas_project":%s,"cas":"%s"}\n' \
    "$proj" "$compiler" "$(have "$pdir/build")" "$caches" \
    "$(have "$cas/objects/aa/aa_lib_$compiler.o")" \
    "$(have "$cas/objects/bb/bb_${proj}_$compiler.o")" "$cas" >> "$root/rz.log"
echo "compiling $proj with $compiler"
if [[ "${FAKE_FAIL_COMPILER:-}" == "$compiler" ]]; then
    echo "error: stub failure" >&2
    exit 1
fi
mkdir -p "$pdir/build/debug" "$pdir/.ritz-cache-$compiler" \
         "$cas/objects/aa" "$cas/meta/aa" "$cas/objects/bb" "$cas/meta/bb"
bin=$(sed -n 's/^name = "\(.*\)"/\1/p' "$pdir/ritz.toml" | sed -n 2p)
printf '#!/usr/bin/env bash\necho "usage: %s"\nexit %s\n' "$bin" "${FAKE_HELP_EXIT:-0}" \
    > "$pdir/build/debug/$bin"
chmod +x "$pdir/build/debug/$bin"
echo o > "$cas/objects/aa/aa_lib_$compiler.o"
echo "{\"module\": \"projects/ritz/ritzlib/sys.ritz\", \"compiler\": \"$compiler\"}" \
    > "$cas/meta/aa/aa_lib_$compiler.json"
echo o > "$cas/objects/bb/bb_${proj}_$compiler.o"
echo "{\"module\": \"projects/$proj/src/main.ritz\", \"compiler\": \"$compiler\"}" \
    > "$cas/meta/bb/bb_${proj}_$compiler.json"
"""

# Stub ritz1 Makefile.  No `ritz1_selfhosted` target, as in the real one:
# asking for it fails, as v1 did without noticing.  `bootstrap` logs the
# build dir it starts from, then writes what the real bootstrap writes.
STUB_MAKEFILE = """\
.PHONY: ritz1 bootstrap clean distclean
ritz1:
\tmkdir -p build
\techo ritz1 >> ../../../make.log
\ttouch build/ritz1 build/main.o build/ritzlib_sys.o
\tchmod +x build/ritz1
bootstrap:
\tmkdir -p build
\techo "bootstrap $$(ls build | tr '\\n' ' ')" >> ../../../make.log
\ttouch build/main_sh.ll build/main_sh.o build/ritz1_selfhosted
\tchmod +x build/ritz1_selfhosted
clean:
\trm -f build/*.ll build/*.o
distclean: clean
\techo distclean >> ../../../make.log
\trm -f build/ritz1 build/ritz1_selfhosted
"""

PROJECTS = {"valet": "valet", "tome": "tome-cli", "zeus": "zeus"}


def _exe(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def fake(tmp_path):
    root = tmp_path / "repo"
    (root / "bench").mkdir(parents=True)
    shutil.copy(COMPILE_SH, root / "bench" / "compile.sh")
    _exe(root / "rz", STUB_RZ)
    for proj, binary in PROJECTS.items():
        p = root / "projects" / proj
        p.mkdir(parents=True)
        (p / "ritz.toml").write_text(
            f'[package]\nname = "{proj}"\n\n[[bin]]\nname = "{binary}"\nentry = "main::main"\n'
        )
    ritz = root / "projects" / "ritz"
    (ritz / "ritz0").mkdir(parents=True)
    (ritz / "ritz0" / "ritz0.py").write_text("print('ritz0')\n")
    (ritz / "ritz1").mkdir()
    (ritz / "ritz1" / "Makefile").write_text(STUB_MAKEFILE)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "init",
        ],
        check=True,
    )
    return root


def run(root: Path, *args, **env):
    full = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("FAKE_", "RITZ_CACHE_DIR"))
    }
    full.update(env)
    return subprocess.run(
        ["bash", str(root / "bench" / "compile.sh"), *args],
        capture_output=True,
        text=True,
        timeout=60,
        env=full,
        check=False,
    )


def rz_log(root: Path) -> list:
    path = root / "rz.log"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def results(json_path: Path) -> list:
    return json.loads(json_path.read_text())["results"]


# ── CLI ────────────────────────────────────────────────────────────────────


def test_help_prints_usage(fake):
    r = run(fake, "--help")
    assert r.returncode == 0, r.stderr
    assert "--compiler" in r.stdout and "--repeat" in r.stdout


def test_unknown_compiler_is_rejected(fake):
    r = run(fake, "--compiler", "ritz0,ritz2", "--dry-run")
    assert r.returncode == 2
    assert "ritz2" in r.stderr


def test_defaults_sweep_all_three_compilers_and_six_projects(fake):
    r = run(fake, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "compilers: ritz0 ritz1 ritz1_selfhosted" in r.stderr
    assert "projects: zeus rzrz tome valet mausoleum nexus" in r.stderr
    assert not (fake / "rz.log").exists(), "--dry-run must build nothing"


# ── The compiler sweep ─────────────────────────────────────────────────────


def test_each_requested_compiler_builds_each_project(fake, tmp_path):
    out = tmp_path / "c.json"
    r = run(
        fake,
        "--compiler",
        "ritz0,ritz1",
        "--projects",
        "valet,tome",
        "--skip-self-build",
        "--json",
        str(out),
    )
    assert r.returncode == 0, r.stderr
    # Each pair is built three times (prime, cold, warm), all with ITS compiler.
    built = Counter((e["compiler"], e["proj"]) for e in rz_log(fake))
    assert built == {
        ("ritz0", "valet"): 3,
        ("ritz0", "tome"): 3,
        ("ritz1", "valet"): 3,
        ("ritz1", "tome"): 3,
    }, built
    swept = {
        (x["compiler"], x["project"]) for x in results(out) if x["phase"] == "cold"
    }
    assert swept == set(built)


def test_cold_purges_project_but_keeps_ritzlib_primed(fake):
    r = run(
        fake,
        "--compiler",
        "ritz0",
        "--projects",
        "valet",
        "--repeat",
        "2",
        "--skip-self-build",
    )
    assert r.returncode == 0, r.stderr
    log = rz_log(fake)
    # prime, then (cold, warm) per sample
    assert len(log) == 5, log
    prime, cold1, warm1, cold2, warm2 = log
    assert not prime["cas_ritzlib"]
    for cold in (cold1, cold2):
        assert cold == {
            **cold,
            "build": False,
            "ritz_cache": False,
            "cas_project": False,
            "cas_ritzlib": True,
        }, cold
    for warm in (warm1, warm2):
        assert warm == {
            **warm,
            "build": True,
            "ritz_cache": True,
            "cas_project": True,
            "cas_ritzlib": True,
        }, warm


def test_benchmark_never_touches_the_shared_cas(fake, tmp_path):
    shared = tmp_path / "shared-cas"
    r = run(
        fake,
        "--compiler",
        "ritz0",
        "--projects",
        "valet",
        "--skip-self-build",
        RITZ_CACHE_DIR=str(shared),
    )
    assert r.returncode == 0, r.stderr
    assert not shared.exists()
    assert {e["cas"] for e in rz_log(fake)} != {str(shared)}


def test_failed_build_is_reported_not_swallowed(fake, tmp_path):
    out = tmp_path / "c.json"
    r = run(
        fake,
        "--compiler",
        "ritz0,ritz1",
        "--projects",
        "valet",
        "--skip-self-build",
        "--json",
        str(out),
        FAKE_FAIL_COMPILER="ritz1",
    )
    assert r.returncode == 1, r.stdout + r.stderr
    status = {(x["compiler"], x["phase"]): x["status"] for x in results(out)}
    assert status[("ritz0", "cold")] == "ok"
    assert status[("ritz1", "cold")] == "fail"
    assert "FAIL" in r.stdout


# ── Output ─────────────────────────────────────────────────────────────────


def test_json_and_markdown_table(fake, tmp_path):
    out = tmp_path / "c.json"
    r = run(
        fake,
        "--compiler",
        "ritz0,ritz1",
        "--projects",
        "valet,zeus",
        "--repeat",
        "2",
        "--skip-self-build",
        "--json",
        str(out),
    )
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text())
    assert doc["settings"]["repeat"] == 2
    assert doc["settings"]["compilers"] == ["ritz0", "ritz1"]
    assert doc["settings"]["projects"] == ["valet", "zeus"]
    head = subprocess.run(
        ["git", "-C", str(fake), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    prov = doc["provenance"]
    assert prov["git_head"] == head
    assert len(prov["compilers"]["ritz0"]) == 64
    assert len(prov["compilers"]["ritz1"]) == 64
    cold = [x for x in doc["results"] if x["phase"] == "cold"]
    assert len(cold) == 2 * 2 * 2  # compilers x projects x samples
    assert all(isinstance(x["seconds"], float) for x in doc["results"])
    assert "| Project | Compiler |" in r.stdout
    rows = [line for line in r.stdout.splitlines() if line.startswith("| valet ")]
    assert len(rows) == 2


def test_help_smoke_status_is_recorded(fake, tmp_path):
    out = tmp_path / "c.json"
    r = run(
        fake,
        "--compiler",
        "ritz0",
        "--projects",
        "tome",
        "--skip-self-build",
        "--json",
        str(out),
        FAKE_HELP_EXIT="3",
    )
    assert r.returncode == 0, r.stderr
    smoke = {x["smoke"] for x in results(out) if x["phase"] == "cold"}
    assert smoke == {"exit 3"}
    assert "exit 3" in r.stdout


# ── ritz1 rebuild and bootstrap timing ─────────────────────────────────────


def test_bootstrap_uses_real_target_and_keeps_ritzlib_objects(fake, tmp_path):
    out = tmp_path / "c.json"
    r = run(
        fake,
        "--compiler",
        "ritz0",
        "--projects",
        "valet",
        "--repeat",
        "2",
        "--json",
        str(out),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    make_log = (fake / "make.log").read_text().splitlines()
    boots = [line.split()[1:] for line in make_log if line.startswith("bootstrap")]
    assert len(boots) == 2, make_log
    for listing in boots:
        assert "ritzlib_sys.o" in listing, listing
        assert not [f for f in listing if "_sh." in f or f == "ritz1_selfhosted"], (
            listing
        )
    phases = [x["phase"] for x in results(out) if x["project"] == "-"]
    assert phases.count("ritz1_clean") == 2 and phases.count("bootstrap") == 2
    assert all(x["status"] == "ok" for x in results(out))
    assert make_log.count("distclean") >= 2


def test_shellcheck_clean():
    sc = shutil.which("shellcheck")
    if not sc:
        pytest.skip("shellcheck not installed")
    r = subprocess.run(
        [sc, str(COMPILE_SH)], capture_output=True, text=True, check=False
    )
    assert r.returncode == 0, r.stdout


@pytest.mark.parametrize("bad", ["0", "x", "-1"])
def test_repeat_must_be_positive(fake, bad):
    r = run(fake, "--repeat", bad, "--dry-run")
    assert r.returncode == 2
    assert "--repeat" in r.stderr
