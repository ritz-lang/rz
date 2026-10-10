#!/usr/bin/env python3
"""
Matrix runner: every [[test]] fn in ritz0/test/*.ritz across 3 compilers.
Run: python3 projects/ritz/tools/run_regression_matrix.py [--tests REGEX] [--compiler all|ritz0|ritz1|ritz1_selfhosted] [-v]
"""

import argparse, os, re, shutil, signal, subprocess, sys, tempfile, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
RITZ_ROOT = THIS_FILE.parent.parent          # projects/ritz
ROOT = RITZ_ROOT.parent.parent               # worktree root
RITZ_PATH_ENV = str(RITZ_ROOT)
TEST_DIR = RITZ_ROOT / "ritz0/test"
RUNTIME_O = RITZ_ROOT / "runtime/ritz_start_envp.x86_64.o"

RITZ0 = [sys.executable, str(RITZ_ROOT / "ritz0/ritz0.py")]
RITZ1 = str(RITZ_ROOT / "ritz1/build/ritz1")
RITZ1_SH = str(RITZ_ROOT / "ritz1/build/ritz1_selfhosted")

# The ritzlib modules compiled and linked into every matrix cell. Every name
# must exist as ritzlib/<name>.ritz; a missing one is a hard error
# (resolve_ritzlib_modules). It used to be a silent `continue`, so "bytes",
# which has never existed in git history and which nothing imports, sat here
# for months as 15 names, 14 links and no diagnostic (AGAST #1345). It was
# deleted, not written: ritzlib/buf.ritz is the byte-buffer module.
#
# This is NOT ritzlib coverage. The list is what the test_issue_* repros need
# to link, a minority of the modules on disk; ritzlib_coverage_line() prints
# the real denominator on every run. Widening it is separate work.
RITZLIB_DIR = RITZ_ROOT / "ritzlib"
RITZLIB_MODULES = ["sys", "io", "str", "strview", "string", "hash", "memory",
                   "gvec", "drop", "env", "option", "result", "hashmap",
                   "span"]

# Cells that are known to fail, keyed by (compiler, test) so an excuse for
# ritz1 never silently covers ritz1_selfhosted — the two disagreeing is a
# self-hosting bug, and scripts/regression.sh's allowlist header is explicit
# that such a divergence must go red rather than be recorded.
#
# Every entry must name an AGAST task (enforced by
# tools/test_run_regression_matrix_gate.py), and the list is STRICT-XPASS: a
# cell listed here that starts passing fails the gate until the line is
# deleted. That is the rule from rz.toml's [ci.known_failing.*] and, since
# AGAST #1365, from scripts/regression.sh too. An allowlist that cannot go red
# is an allowlist nobody edits — #1365 found two entries blaming the async
# framework for what was really a syntax migration.
EXPECTED_FAILURES = {
    ("ritz1", "test_issue_float_coercion"):
        "AGAST #1370 — ritz1 has no float method dispatch; x.ceil() fails even "
        "with an identifier receiver. It previously 'passed' because the "
        "emitter substituted a zero and said nothing (#1369), and because the "
        "matrix only runs the file's FIRST [[test]] fn (#1371) — the assertion "
        "that would have caught it is the third.",
    ("ritz1_selfhosted", "test_issue_float_coercion"):
        "AGAST #1370 — same gap, listed separately on purpose: an excuse for "
        "ritz1 must not cover its self-compiled twin.",
}

# AGAST #1371 — what the matrix found once it ran every [[test]] fn of every
# file instead of fns[0] of 53. Each failure was triaged to a root cause and
# ticketed individually; stale tests (assert c"msg", printf-style prints,
# string_from(c"..."), a String Drop bound, a named asm label) were MIGRATED,
# not listed. What remains is below, one ticket per root cause.
#
# Keys: "file" excuses build failures only (compile/asm/link — they hit every
# fn at once); "file::fn" excuses one fn's runtime failure. A file with several
# causes cites the first blocker and names the rest, so whoever fixes the first
# sees the entry go stale (xpass) or keep failing for a listed reason.
#
# These hold for ritz1 AND ritz1_selfhosted, which fail identically today, so
# they are written once and expanded per compiler. That does not let one
# excuse the other: each is still its own key, and if the twins ever diverge
# the passing one turns xpass and the gate goes red.
_RITZ1_TWINS = {
    # --- codegen, build failures ---
    "test_mut_ref":
        "AGAST #1607 — instance-method args not narrowed to param width (invalid IR)",
    "test_level12":
        "AGAST #1608 — struct literal nested in a field/array literal rejected",
    "test_aesni":
        "AGAST #1609 — AES-NI intrinsics do not bitcast v4i32 operands",
    "test_level34":
        "AGAST #1610 — bare user-enum unit variant as a value is an unknown identifier",
    "test_native_string":
        "AGAST #1627 — unspecified ritz0-only String coercions (\"...\"→String, String→*u8)",
    "test_string_coercion":
        "AGAST #1627 — unspecified ritz0-only String→*u8 coercion",
    "test_level22":
        "AGAST #1519 — `Vec<*u8>` annotation mangles to `Vec$` (invalid IR vs "
        "`Vec$ptr_u8`)",
    "test_level23":
        "AGAST #1514 — `let tmp: T` in a generic fn becomes `alloca %T$i32` "
        "(unsized type)",
    "test_level32":
        "AGAST #1634 — unspecified ritz0-only `Box<T>` implicit field deref "
        "(`b.x`); ritz1: unhandled EXPR_MEMBER",
    "test_level33":
        "AGAST #1635 — unspecified ritz0-only `m[k]` sugar for HashMapI64; ritz1 "
        "emits invalid IR",
    # --- grammar / missing features ---
    "test_level25":
        "AGAST #1607 — `p.move_by(10, 20)`: instance-method args not narrowed "
        "to param width (invalid IR)",
    "test_level30":
        "AGAST #1520 — methods of a generic impl (`impl<T> Describable for "
        "Wrapper<T>`) are never specialized: undefined `Wrapper$i64_describe`",
    "test_level40":
        "AGAST #1620 — `dyn Trait`",
    "test_trait_bounds":
        "AGAST #1621 — trait bounds on generic params; also AGAST #1612 "
        "(multi-arg generic calls)",
    "test_issue_slice_generic_payload":
        "AGAST #1614 — slice type `[T]` (ritz0-only sugar)",
    "test_issue_slice_generic_siblings":
        "AGAST #1614 — `[T]`; also AGAST #1613 (if-expression), #1615 (2.5f32), "
        "#1616 (empty []), #1617 (assignment match-arm bodies)",
    "test_issue_struct_enum_variants":
        "AGAST #1295 — payload-carrying user enums / struct variants / N-ary "
        "patterns; also AGAST #1617 (assignment match-arm bodies)",
    "test_level24":
        "AGAST #1622 — union type aliases + type-name patterns",
    "test_level39":
        "AGAST #1623 — closures / anonymous fns (spec says not implemented)",
    "test_issue99":
        "AGAST #1624 — `alias::item` calls, removed from the spec; ritz0 is the outlier",
    "test_asm":
        "AGAST #1619 — inline `asm x86_64:` blocks unsupported in ritz1",
}

# Files no compiler can build: they target draft features (LARB-0013) that
# exist in no implementation. Listed for all three compilers.
_ALL_COMPILERS = {
    "test_level41": "AGAST #1625 — `defer` is reserved but implemented nowhere",
    "test_level42": "AGAST #1626 — `[[cfg(...)]]` is implemented nowhere",
}

for _key, _reason in _RITZ1_TWINS.items():
    EXPECTED_FAILURES[("ritz1", _key)] = _reason
    EXPECTED_FAILURES[("ritz1_selfhosted", _key)] = _reason
for _key, _reason in _ALL_COMPILERS.items():
    for _c in ("ritz0", "ritz1", "ritz1_selfhosted"):
        EXPECTED_FAILURES[(_c, _key)] = _reason


def matrix_outcome(compiler, results, expected):
    """Classify one compiler's results against the expected-failure list.

    Mirrors rz's gate_outcome (rz:135) so the workspace has one grammar for
    this, not two that drift.

    Returns (hard, known, xpass), each a sorted list of test names:
      hard  — failed and not expected. Fails the gate.
      known — failed and expected. Advisory; printed with its AGAST reference.
      xpass — expected to fail but passed. Also fails the gate, so the entry
              gets deleted rather than accumulating.

    Only tests that actually RAN are considered, so `--tests <regex>` cannot
    turn every unselected entry into a spurious xpass.
    """
    hard, known, xpass = [], [], []
    results = {u: r for u, r in results.items() if r[0] not in SKIP_STATUSES}
    for unit, (status, _code, _info) in results.items():
        if status == "pass":
            continue
        if excuse_for(compiler, unit, status, expected):
            known.append(unit)
        else:
            hard.append(unit)
    # Strict-xpass, per entry. A per-fn entry is stale once that fn passes; a
    # file-level entry is stale once the file builds (every unit ran past the
    # build stage) — remaining runtime failures then need per-fn entries.
    for c, key in expected:
        if c != compiler:
            continue
        if "::" in key:
            if key in results and results[key][0] == "pass":
                xpass.append(key)
            continue
        units = [r for u, r in results.items() if u == key or u.startswith(key + "::")]
        if units and not any(r[0] in BUILD_STATUSES for r in units):
            xpass.append(key)
    return sorted(hard), sorted(known), sorted(xpass)


def matrix_exit_code(outcomes):
    """0 only when no compiler has a hard failure or an xpass.

    This function existing at all is the fix for AGAST #1372: main() used to
    end in an unconditional `return 0`, so `make matrix-full` — the gate cited
    in nearly every commit message in this repo, and a CI step — exited 0 with
    red cells in its own printed summary.
    """
    for hard, _known, xpass in outcomes.values():
        if hard or xpass:
            return 1
    return 0


# ---------------------------------------------------------------------------
# What runs (AGAST #1371)
#
# This used to be TESTS, a hardcoded list of 53 file names, and the harness
# called only fns[0] — the FIRST [[test]] fn in each file. "53/53 × 3" meant
# 53 of the 560 [[test]] fns in ritz0/test/ had executed. The list never
# grew (66 files on disk were never in it) and 20 fns inside its own files
# never ran, including the float_coercion assertion #1370 later found broken.
#
# Now every *.ritz file in TEST_DIR is discovered, every [[test]] fn in it is a
# separate unit ("file::fn"), and floor_violations() fails the gate if any
# [[test]] line on disk did not produce an executed unit. A list goes stale;
# a floor does not.
# ---------------------------------------------------------------------------

# Files in TEST_DIR that are not tests: no [[test]] fn and no main, so there
# is nothing to execute. Enforced by test_not_tests_entries_really_have_
# nothing_to_run — a file here that grows a test or a main must leave.
NOT_TESTS = {
    "test_import_lib":
        "library imported by test_import_main.ritz; it is compiled and linked "
        "as part of that file's import closure",
}

# A failing file's units are run one process each, selected by a one-byte
# argv[1]: chr(SELECTOR_BASE + index). Printable ASCII from '!'.
SELECTOR_BASE = 33
MAX_FNS_PER_FILE = 126 - SELECTOR_BASE + 1

# Statuses produced before anything executes. A file-level EXPECTED_FAILURES
# entry may only excuse these — a runtime failure needs a per-fn entry.
BUILD_STATUSES = frozenset({"compile-fail", "asm-fail", "link-fail", "deps-fail"})

# Not run because the host CPU cannot execute the file's instructions. Printed
# on every run; never a pass, never a failure, never makes an entry xpass.
SKIP_STATUSES = frozenset({"skip-cpu"})

# Files whose tests execute ISA extensions, keyed to /proc/cpuinfo flags. Objects
# are built with -march=native (as ritz0/test_runner.py does), so on a host
# with the flag they compile and run; on one without, they are skipped rather
# than reported as compiler failures. sha_ni is absent on many x86 hosts.
REQUIRES_CPU = {
    "test_aesni": ["aes"],
    "test_avx2": ["avx2"],
    "test_shani": ["sha_ni"],
    "test_simd": ["pclmulqdq", "sse4_1"],
}

CLANG_C = ["clang", "-c", "-O2", "-march=native"]

_MARKER_RE = re.compile(r"^\s*\[\[test\]\]\s*$", re.MULTILINE)
_FN_RE = re.compile(r"^fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\)\s*(?:->\s*(\w+))?\s*$")
_MAIN_RE = re.compile(r"^fn\s+main\s*\(", re.MULTILINE)


def strip_main(src):
    lines = src.split("\n")
    out = []
    skip = False
    for line in lines:
        if skip:
            if line.strip() == "":
                continue
            if not (line.startswith(" ") or line.startswith("\t")):
                skip = False
            else:
                continue
        if re.match(r"^fn\s+main\s*\(", line):
            skip = True
            continue
        out.append(line)
    return "\n".join(out)


def cpu_flags():
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("flags"):
                return set(line.split(":", 1)[1].split())
    except OSError:
        pass
    return set()


def cpu_skip_reason(test_name, flags, requires=None):
    requires = REQUIRES_CPU if requires is None else requires
    missing = [f for f in requires.get(test_name, []) if f not in flags]
    return f"host CPU lacks {', '.join(missing)}" if missing else None


def discover_test_files(test_dir=None, not_tests=None):
    """Every *.ritz stem in test_dir except NOT_TESTS, sorted."""
    test_dir = TEST_DIR if test_dir is None else Path(test_dir)
    not_tests = NOT_TESTS if not_tests is None else not_tests
    return sorted(p.stem for p in Path(test_dir).glob("*.ritz") if p.stem not in not_tests)


def count_test_markers(src):
    """[[test]] lines, counted without the fn parser, so the floor can compare."""
    return len(_MARKER_RE.findall(src))


def find_test_fns(src):
    """[(name, return_type)] for each [[test]] fn; return_type is None for void."""
    out = []
    lines = src.split("\n")
    i = 0
    while i < len(lines):
        if _MARKER_RE.match(lines[i]):
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines):
                m = _FN_RE.match(lines[j].rstrip())
                if m:
                    out.append((m.group(1), m.group(2)))
            i = j
            continue
        i += 1
    return out


def units_for(test_name, src):
    """The executable units of one file: one per [[test]] fn, else its main."""
    fns = find_test_fns(src)
    if fns:
        return [f"{test_name}::{name}" for name, _ in fns]
    if _MAIN_RE.search(src):
        return [f"{test_name}::main"]
    return []


def selector_arg(index):
    if not 0 <= index < MAX_FNS_PER_FILE:
        raise ValueError(f"test fn index {index} exceeds MAX_FNS_PER_FILE={MAX_FNS_PER_FILE}")
    return chr(SELECTOR_BASE + index)


def build_harness(src, fns):
    """The file without its main, plus a main that runs fns[argv[1]].

    A test fn's i32 result reaches the process exit status, which keeps only
    the low 8 bits — ritz_matrix_rc maps a nonzero multiple of 256 to 255 so
    it cannot read as a pass. Void test fns pass by returning (assert exits).
    """
    if len(fns) > MAX_FNS_PER_FILE:
        raise ValueError(f"{len(fns)} test fns exceeds MAX_FNS_PER_FILE")
    arms = []
    for i, (name, ret) in enumerate(fns):
        arms.append(f"    if ritz_matrix_k == {SELECTOR_BASE + i}")
        if ret == "i64":
            arms.append(f"        return ritz_matrix_rc64({name}())")
        elif ret is None:
            arms.append(f"        {name}()")
            arms.append("        return 0")
        else:
            arms.append(f"        return ritz_matrix_rc({name}())")
    return (strip_main(src) + "\n\n"
            "fn ritz_matrix_rc(r: i32) -> i32\n"
            "    if r != 0\n"
            "        if (r & 255) == 0\n"
            "            return 255\n"
            "    r\n\n"
            "fn ritz_matrix_rc64(r: i64) -> i32\n"
            "    if r == 0\n"
            "        return 0\n"
            "    let lo: i64 = r & 255\n"
            "    if lo == 0\n"
            "        return 255\n"
            "    lo as i32\n\n"
            "fn main(ritz_matrix_argc: i32, ritz_matrix_argv: **u8, ritz_matrix_envp: **u8) -> i32\n"
            "    if ritz_matrix_argc < 2\n"
            "        return 125\n"
            "    let ritz_matrix_sel: *u8 = ritz_matrix_argv[1]\n"
            "    let ritz_matrix_k: i32 = ritz_matrix_sel[0] as i32\n"
            + "\n".join(arms) + "\n"
            "    126\n")


def excuse_for(compiler, unit, status, expected):
    """The EXPECTED_FAILURES key that excuses this failing unit, or None.

    A per-fn entry excuses any failure of that fn. A file-level entry excuses
    only build-stage failures, which by nature hit every fn in the file at once
    and cannot be attributed to one; letting it cover runtime failures would
    make a single line a bulk allowlist for the whole file.
    """
    if (compiler, unit) in expected:
        return (compiler, unit)
    file_name = unit.partition("::")[0]
    if status in BUILD_STATUSES and (compiler, file_name) in expected:
        return (compiler, file_name)
    return None


def floor_violations(srcs, results):
    """Reasons the run executed less than what is on disk (empty = OK).

    srcs: {file_name: source} for the files selected this run.
    results: {compiler: {unit: (status, code, info)}}.
    """
    out = []
    expected_units = []
    for name, src in sorted(srcs.items()):
        markers = count_test_markers(src)
        parsed = len(find_test_fns(src))
        if markers != parsed:
            out.append(f"{name}: {markers} [[test]] line(s) but {parsed} parsed test fn(s) — "
                       f"find_test_fns cannot read a test signature; fix the parser, "
                       f"do not let the fn drop out")
        units = units_for(name, src)
        if not units and markers == 0:
            out.append(f"{name}: no [[test]] fn and no main, so nothing runs — add a test "
                       f"or list it in NOT_TESTS with a reason")
        expected_units.extend(units)
    for compiler, res in sorted(results.items()):
        missing = [u for u in expected_units if u not in res]
        if missing:
            out.append(f"{compiler}: {len(missing)} of {len(expected_units)} unit(s) never "
                       f"ran: {', '.join(missing[:10])}{' …' if len(missing) > 10 else ''}")
    return out

def compile_with_ritz0(src_path, out_ll, env):
    cmd = RITZ0 + [str(src_path), "-o", str(out_ll), "--no-runtime",
                   "--project-root", RITZ_PATH_ENV]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)


def compile_with_ritz1(binary, src_path, out_ll, env):
    cmd = [binary, str(src_path), "-o", str(out_ll)]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)


def resolve_ritzlib_modules(modules=None, ritzlib_dir=None):
    """(sources, missing) for the named ritzlib modules, in list order.

    Defaults are resolved at call time, not bound as default arguments, so
    a test that monkeypatches RITZLIB_MODULES is honoured.
    """
    modules = RITZLIB_MODULES if modules is None else modules
    ritzlib_dir = RITZLIB_DIR if ritzlib_dir is None else Path(ritzlib_dir)
    srcs, missing = [], []
    for mod in modules:
        src = ritzlib_dir / f"{mod}.ritz"
        if src.is_file():
            srcs.append(src)
        else:
            missing.append(mod)
    return srcs, missing


def ritzlib_coverage_line(modules=None, ritzlib_dir=None):
    """Say how much of ritzlib the matrix links, so green is not over-read."""
    modules = RITZLIB_MODULES if modules is None else modules
    ritzlib_dir = RITZLIB_DIR if ritzlib_dir is None else Path(ritzlib_dir)
    on_disk = len(list(ritzlib_dir.glob("*.ritz")))
    return (f"# Linking {len(modules)} of {on_disk} ritzlib modules on disk "
            f"(RITZLIB_MODULES). A green matrix does NOT mean ritzlib is covered.")


def build_ritzlib_objs(tmpdir, env):
    srcs, missing = resolve_ritzlib_modules()
    if missing:
        return None, (f"RITZLIB_MODULES names module(s) with no source file in "
                      f"{RITZLIB_DIR}: {', '.join(missing)}. Write the module "
                      f"or delete the name, and say which in the commit.")
    objs = []
    for src in srcs:
        mod = src.stem
        ll = Path(tmpdir) / f"ritzlib_{mod}.ll"
        o = Path(tmpdir) / f"ritzlib_{mod}.o"
        cmd = RITZ0 + [str(src), "-o", str(ll), "--no-runtime",
                       "--project-root", RITZ_PATH_ENV]
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
        if r.returncode != 0:
            return None, f"ritzlib {mod} compile failed: {r.stderr[-300:]}"
        cmd = CLANG_C + [str(ll), "-o", str(o)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return None, f"ritzlib {mod} asm failed: {r.stderr[-300:]}"
        objs.append(str(o))
    return objs, None


class DepObjects:
    """ritz0-compiled objects for a test file's import closure, built once.

    RITZLIB_MODULES is the baseline linked into every cell. A file importing
    anything else (ritzlib.box, ritzlib.uring, a sibling like test_import_lib)
    would otherwise link-fail for a reason that is not a compiler bug, so its
    transitive closure (ritz0/list_deps.py) is compiled and linked on top.
    """

    def __init__(self, tmpdir, env, baseline_srcs, baseline_objs):
        self.tmpdir = Path(tmpdir)
        self.env = env
        self.baseline = {str(Path(s).resolve()) for s in baseline_srcs}
        self.baseline_objs = list(baseline_objs)
        self._objs = {}
        self._lock = threading.Lock()
        self._key_locks = {}
        self.cpu_flags = cpu_flags()

    def closure(self, src_path):
        """Absolute paths of src_path's imports (excluding itself), or raise."""
        r = subprocess.run(RITZ0[:1] + [str(RITZ_ROOT / "ritz0/list_deps.py"), str(src_path),
                                        "--project-root", RITZ_PATH_ENV],
                           capture_output=True, text=True, env=self.env, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f"list_deps failed: {r.stderr[-300:]}")
        me = str(Path(src_path).resolve())
        return [p for p in r.stdout.split() if str(Path(p).resolve()) != me]

    def obj_for(self, dep):
        """Object for one dependency source; (obj, None) or (None, error)."""
        key = str(Path(dep).resolve())
        with self._lock:
            if key in self._objs:
                return self._objs[key]
            klock = self._key_locks.setdefault(key, threading.Lock())
        with klock:
            with self._lock:
                if key in self._objs:
                    return self._objs[key]
            tag = f"dep_{abs(hash(key)) & 0xFFFFFFFF:08x}_{Path(dep).stem}"
            ll, o = self.tmpdir / f"{tag}.ll", self.tmpdir / f"{tag}.o"
            r = subprocess.run(RITZ0 + [dep, "-o", str(ll), "--no-runtime",
                                        "--project-root", RITZ_PATH_ENV],
                               capture_output=True, text=True, env=self.env, timeout=120)
            if r.returncode == 0:
                r = subprocess.run(CLANG_C + [str(ll), "-o", str(o)],
                                   capture_output=True, text=True, timeout=120)
            res = (str(o), None) if r.returncode == 0 else (
                None, f"{Path(dep).name}: {r.stderr[-300:]}")
            with self._lock:
                self._objs[key] = res
            return res

    def baseline_archive(self):
        """The baseline objects as one static archive, built once.

        Linked as an archive, not as loose objects, so ld pulls in a module
        only to resolve a symbol nothing else defines. Loose objects made
        test_cstring -- which defines its own strlen, as a test file may --
        link-fail against ritzlib/str.o on a symbol it never asked for.
        """
        with self._lock:
            if getattr(self, "_archive", None):
                return self._archive
            a = self.tmpdir / "ritzlib_baseline.a"
            subprocess.run(["ar", "rcs", str(a)] + self.baseline_objs,
                           check=True, capture_output=True, timeout=60)
            self._archive = str(a)
            return self._archive

    def link_objs(self, closure):
        """(objs, None) or (None, error): the closure's non-baseline objects.

        The baseline itself is linked separately, as baseline_archive().
        """
        objs = []
        for dep in closure:
            if str(Path(dep).resolve()) in self.baseline:
                continue
            o, err = self.obj_for(dep)
            if err:
                return None, err
            objs.append(o)
        return objs, None


def run_file(test_name, compiler_name, compiler_bin, deps, env, tmpdir):
    """{unit: (status, code, info)} for every unit of one file under one compiler.

    The file is compiled once into a harness that dispatches on argv[1]; each
    test fn then runs in its own process, so one fn's crash or failure is
    attributed to that fn and cannot hide its siblings.
    """
    src_path = TEST_DIR / f"{test_name}.ritz"
    src = src_path.read_text()
    units = units_for(test_name, src)
    if not units:
        return {test_name: ("no-test-fn", 0, f"no [[test]] fn and no main in {test_name}")}
    fns = find_test_fns(src)

    def all_units(status, code, info):
        return {u: (status, code, info) for u in units}

    work = Path(tmpdir) / compiler_name / test_name
    work.mkdir(parents=True, exist_ok=True)
    skip = cpu_skip_reason(test_name, deps.cpu_flags)
    if skip:
        return all_units("skip-cpu", 0, skip)
    try:
        closure = deps.closure(src_path)
    except RuntimeError:
        # ritz0's import resolver could not parse the file. Link only the
        # baseline and let the compiler under test report its own diagnostic,
        # so the cell says what that compiler thinks, not what list_deps does.
        closure = []
    # Sibling modules (import test_import_lib) must resolve from the wrapper's
    # directory too, for compilers that read their declarations.
    for dep in closure:
        if Path(dep).resolve().parent == TEST_DIR.resolve():
            shutil.copy(dep, work / Path(dep).name)
    objs, err = deps.link_objs(closure)
    if err:
        return all_units("deps-fail", 1, err)

    harness = build_harness(src, fns) if fns else src
    wrap = work / f"{test_name}.ritz"
    wrap.write_text(harness)

    out_ll = work / f"{test_name}.ll"
    try:
        if compiler_name == "ritz0":
            r = compile_with_ritz0(wrap, out_ll, env)
        else:
            r = compile_with_ritz1(compiler_bin, wrap, out_ll, env)
    except subprocess.TimeoutExpired:
        return all_units("compile-fail", 124, "compiler timeout")
    if r.returncode != 0:
        return all_units("compile-fail", r.returncode, r.stderr[-400:])

    obj = work / f"{test_name}.o"
    r = subprocess.run(CLANG_C + [str(out_ll), "-o", str(obj)],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return all_units("asm-fail", r.returncode, r.stderr[-400:])

    exe = work / f"{test_name}.exe"
    link_cmd = (["ld", "-dynamic-linker", "/lib64/ld-linux-x86-64.so.2", "-lc",
                 "-o", str(exe), str(RUNTIME_O), str(obj)] + objs
                + [deps.baseline_archive()])
    r = subprocess.run(link_cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return all_units("link-fail", r.returncode, r.stderr[-400:])

    out = {}
    for i, unit in enumerate(units):
        argv = [str(exe), selector_arg(i)] if fns else [str(exe)]
        out[unit] = run_exe(argv)
    return out


def run_exe(argv):
    try:
        r = subprocess.run(argv, capture_output=True, timeout=10)
    except subprocess.TimeoutExpired:
        return ("timeout", 124, "timeout")
    code = r.returncode
    if code < 0:
        try:
            name = signal.Signals(-code).name
        except ValueError:
            name = f"SIG{-code}"
        return ("signal", code, name)
    if code == 0:
        return ("pass", 0, "")
    err = r.stderr.decode("utf-8", errors="replace").strip()
    if code in (125, 126):
        # 126 is the harness's fall-through: no arm matched the selector. With
        # a correct harness that means the selected fn let control escape --
        # in practice undefined behaviour the optimiser turned into a
        # fall-through (seen: ritz1 loading a global array through null).
        return ("harness", code, f"harness fell through (selector unmatched or UB in test fn) {err[:200]}")
    return ("bad-exit", code, err[:300])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", default=".*",
                    help="regex over file names (e.g. test_issue_) to select files")
    ap.add_argument("--compiler", default="all",
                    choices=["all", "ritz0", "ritz1", "ritz1_selfhosted"])
    ap.add_argument("--jobs", "-j", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--rebuild", action="store_true",
                    help="Rebuild ritz1 and ritz1_selfhosted before running. "
                         "Use after editing ritz1 source so the selfhosted "
                         "binary reflects the changes too.")
    args = ap.parse_args()

    env = os.environ.copy()
    env["RITZ_PATH"] = RITZ_PATH_ENV

    if args.rebuild:
        print("# Rebuilding ritz1 + ritz1_selfhosted...", flush=True)
        ritz1_dir = RITZ_ROOT / "ritz1"
        r = subprocess.run(["make", "-C", str(ritz1_dir), "bootstrap"],
                           env=env, timeout=600)
        if r.returncode != 0:
            print(f"FATAL: make bootstrap failed (rc={r.returncode})")
            return 3

    compilers = []
    if args.compiler in ("all", "ritz0"):
        compilers.append(("ritz0", None))
    if args.compiler in ("all", "ritz1"):
        compilers.append(("ritz1", RITZ1))
    if args.compiler in ("all", "ritz1_selfhosted"):
        compilers.append(("ritz1_selfhosted", RITZ1_SH))

    test_re = re.compile(args.tests)
    tests = [t for t in discover_test_files() if test_re.search(t)]
    srcs = {t: (TEST_DIR / f"{t}.ritz").read_text() for t in tests}

    with tempfile.TemporaryDirectory(prefix="matrix_") as tmpdir:
        print(ritzlib_coverage_line(), flush=True)
        n_units = sum(len(units_for(t, s)) for t, s in srcs.items())
        print(f"# {len(tests)} test files, {n_units} units "
              f"({sum(count_test_markers(s) for s in srcs.values())} [[test]] fns) "
              f"× {len(compilers)} compiler(s), -j{args.jobs}", flush=True)
        print(f"# Building ritzlib objects in {tmpdir} ...", flush=True)
        ritzlib_objs, err = build_ritzlib_objs(tmpdir, env)
        if err:
            print(f"FATAL: {err}")
            return 2
        baseline_srcs, _ = resolve_ritzlib_modules()
        deps = DepObjects(tmpdir, env, baseline_srcs, ritzlib_objs)

        results = {c: {} for c, _ in compilers}
        jobs = [(t, c, b) for t in tests for c, b in compilers]
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            futs = {pool.submit(run_file, t, c, b, deps, env, tmpdir): (t, c) for t, c, b in jobs}
            done = {}
            for fut in as_completed(futs):
                done[futs[fut]] = fut.result()
        for test_name in tests:
            for cname, _ in compilers:
                file_res = done[(test_name, cname)]
                results[cname].update(file_res)
                bad = {u: r for u, r in file_res.items() if r[0] != "pass"}
                tag = "OK" if not bad else "FAIL"
                suffix = f" {len(file_res) - len(bad)}/{len(file_res)}"
                if bad:
                    statuses = sorted({r[0] for r in bad.values()})
                    suffix += f" [{', '.join(statuses)}]"
                print(f"  {cname:20s} {test_name:45s} {tag}{suffix}", flush=True)

        print("\n=== Summary (test fns passed / run) ===")
        for cname, _ in compilers:
            passed = sum(1 for r in results[cname].values() if r[0] == "pass")
            skipped = sum(1 for r in results[cname].values() if r[0] in SKIP_STATUSES)
            total = len(results[cname])
            note = f"  ({skipped} skipped: host CPU, see REQUIRES_CPU)" if skipped else ""
            print(f"  {cname:20s} {passed}/{total}{note}")

        print("\n=== Failures by compiler ===")
        for cname, _ in compilers:
            fails = [(t, r) for t, r in results[cname].items() if r[0] != "pass"]
            if not fails:
                continue
            print(f"\n-- {cname} ({len(fails)} failures) --")
            for t, (status, code, info) in sorted(fails):
                detail = info if args.verbose else info[:120]
                print(f"  {t}: {status} (code={code}) {detail}".replace("\n", " ⏎ "))

        # AGAST #1372 — classify, report, and let the outcome reach the exit
        # code. AGAST #1371 — plus the floor: what ran must cover what is on
        # disk, or the gate is red no matter how green the cells are.
        outcomes = {
            cname: matrix_outcome(cname, results[cname], EXPECTED_FAILURES)
            for cname, _ in compilers
        }
        floor = floor_violations(srcs, results)
        print("\n=== Gate ===")
        for cname, (hard, known, xpass) in outcomes.items():
            if hard:
                by_file = {}
                for u in hard:
                    by_file.setdefault(u.partition("::")[0], []).append(u)
                print(f"  ✗ {cname}: {len(hard)} unexpected failure(s) in {len(by_file)} file(s):")
                for f, us in sorted(by_file.items()):
                    st = sorted({results[cname][u][0] for u in us})
                    print(f"      {f}: {len(us)} fn [{', '.join(st)}]")
            excused = {}
            for u in known:
                key = excuse_for(cname, u, results[cname][u][0], EXPECTED_FAILURES)
                excused.setdefault(key, []).append(u)
            for key, us in sorted(excused.items()):
                print(f"  ⚠ {cname}: {key[1]} ({len(us)} fn) — {EXPECTED_FAILURES[key]}")
            for t in xpass:
                print(f"  ✗ {cname}: {t} is in EXPECTED_FAILURES but no longer fails "
                      f"that way — delete or narrow that entry in tools/run_regression_matrix.py")
        for v in floor:
            print(f"  ✗ floor: {v}")
        rc = matrix_exit_code(outcomes)
        if floor:
            rc = 1
        print("  ✓ matrix gate green" if rc == 0 else "  💥 matrix gate FAILED")

    return rc


if __name__ == "__main__":
    sys.exit(main())
