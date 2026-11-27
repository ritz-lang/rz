"""AGAST #4853: ritz1 declares an imported or extern fn by its real prototype.

ritz1 declared every callee another object defines as `declare T @f(...)`
and called it with i64 for each pointer (`call i32 @memcmp(i64, i64, i64)`).
LLVM's TargetLibraryInfo matches a libc name only against its prototype, and
argument attribute inference wants real `ptr` params. So a callee whose
params and return are all pointers and sized ints is now declared with them
(`declare i32 @memcmp(ptr, ptr, i64)`) and called the same way, the i64
value model bridged at the call site by inttoptr / ptrtoint until #73 makes
pointers native.

What does not change: a callee this .ll defines (its `define` keeps ritz1's
i64 signature, so the call must too); a callee with any other param or
return kind (struct, bool, float, `@T`, `@&T`) keeps the `(...)` declare;
every declare stays "no-builtins" (#1985), which
test_ritz1_o2_libc_names.py's -O2 realloc check now exercises for real.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz1", "ritz1_selfhosted"]

LIB = """\
pub struct Pair
    a: i64
    b: i64

impl Pair
    pub fn at(self: *Pair, p: *u8) -> *u8
        p + self.a

pub fn lib_ptr(p: *u8, n: i32) -> *u8
    p + n as i64

pub fn lib_pp(pp: **u8) -> *u8
    *pp

pub fn lib_u16(x: u16) -> u16
    x + 1

pub fn lib_pair(p: Pair) -> i64
    p.a + p.b

pub fn lib_flag(b: bool) -> i64
    if b then 1 else 0

pub fn lib_ref(p: @&Pair) -> i64
    p.a

pub fn lib_self_call(p: *u8, n: i64) -> *u8
    if n == 0
        return p
    lib_self_call(p + 1, n - 1)
"""

SRC = """\
import ritzlib.memory
import ritzlib.str
import ritzlib.cstr
import r4853lib

extern fn r4853_ext(p: *u8, n: i64) -> i32

fn main() -> i32
    let a: *u8 = malloc(16)
    let b: *u8 = malloc(16)
    memset(a, 7 as u8, 16)
    memcpy(b, a, 16)
    if memcmp(a, b, 16) != 0
        return 2
    *(a + 15) = 0
    if strlen(a) != 15
        return 3
    let c: *u8 = realloc(a, 64)
    if c == null
        return 4
    if lib_ptr(c, 3) != c + 3
        return 5
    var slot: *u8 = b
    if lib_pp(@slot) != b
        return 6
    if lib_u16(41 as u16) != 42
        return 7
    if lib_pair(Pair { a: 1, b: 2 }) + lib_flag(true) != 4
        return 8
    var pr: Pair = Pair { a: 5, b: 0 }
    if lib_ref(@&pr) != 5
        return 9
    if pr.at(b) != b + 5
        return 10
    free(c)
    free(b)
    40
"""

# The same program minus the extern, which nothing defines, for the run.
RUN_SRC = SRC.replace("extern fn r4853_ext(p: *u8, n: i64) -> i32\n", "")

TYPED = {
    "memcmp": "i32 @memcmp(ptr, ptr, i64)",
    "memcpy": "ptr @memcpy(ptr, ptr, i64)",
    "memset": "ptr @memset(ptr, i8, i64)",
    "malloc": "ptr @malloc(i64)",
    "free": "void @free(ptr)",
    "realloc": "ptr @realloc(ptr, i64)",
    "strlen": "i64 @strlen(ptr)",
    "lib_ptr": "ptr @lib_ptr(ptr, i32)",
    "lib_pp": "ptr @lib_pp(ptr)",
    "lib_u16": "i16 @lib_u16(i16)",
}

# An impl method keeps it too: the method emitter's call is untyped.
UNTYPED = ("lib_pair", "lib_flag", "lib_ref", "Pair_at")


def _emit(request, compiler: str, tmp_path: Path, name: str = "t.ritz",
          src_text: str = SRC, extra: tuple = ()) -> str:
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    (tmp_path / "r4853lib.ritz").write_text(LIB)
    src = tmp_path / name
    if name != "r4853lib.ritz":
        src.write_text(src_text)
    ll = tmp_path / (src.stem + ".ll")
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    proc = subprocess.run([str(binary), str(src), "-o", str(ll), *extra],
                          cwd=tmp_path, env=env, capture_output=True,
                          text=True, timeout=300)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]
    return ll.read_text()


def _declare(ir: str, name: str) -> str:
    m = re.search(rf'^declare [^\n]*@"?{re.escape(name)}"?\(.*$', ir, re.M)
    assert m, f"no declaration of {name}"
    return m.group(0)


def _calls(ir: str, name: str) -> list[str]:
    return re.findall(rf'^\s*(?:%\S+ = )?call [^\n]*@{re.escape(name)}\(.*$',
                      ir, re.M)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_pointer_and_int_callees_are_declared_by_their_prototype(
        request, tmp_path, compiler):
    ir = _emit(request, compiler, tmp_path)
    for name, proto in TYPED.items():
        decl = _declare(ir, name)
        assert f"declare {proto}" in decl, decl
        assert '"no-builtins"' in decl, decl
    ext = _declare(ir, "r4853_ext")
    assert "declare i32 @r4853_ext(ptr, i64)" in ext, ext


@pytest.mark.parametrize("compiler", COMPILERS)
def test_call_sites_pass_ptr_and_take_ptr_back(request, tmp_path, compiler):
    ir = _emit(request, compiler, tmp_path)
    for name, proto in TYPED.items():
        params = proto[proto.index("(") + 1:-1].split(", ")
        calls = _calls(ir, name)
        assert calls, f"no call of {name}"
        for call in calls:
            args = call[call.index(f"@{name}(") + len(name) + 2:].rstrip(")")
            kinds = [a.split(" ")[0] for a in args.split(", ")]
            assert kinds == params, call
            # Each `ptr` operand is the inttoptr of an i64 value.
            for arg in args.split(", "):
                if arg.startswith("ptr "):
                    reg = re.escape(arg.split(" ")[1])
                    assert re.search(rf"^\s*{reg} = inttoptr i64 ", ir, re.M), call
    # A pointer result comes back into the i64 value model.
    m = re.search(r"^\s*(%\S+) = call ptr @malloc\(", ir, re.M)
    assert m, ir
    assert re.search(rf"= ptrtoint ptr {re.escape(m.group(1))} to i64", ir), ir


@pytest.mark.parametrize("compiler", COMPILERS)
def test_other_param_kinds_keep_the_untyped_declare(request, tmp_path, compiler):
    ir = _emit(request, compiler, tmp_path)
    for name in UNTYPED:
        decl = _declare(ir, name)
        assert re.search(rf"@{name}\(\.\.\.\)", decl), decl


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_callee_this_file_defines_keeps_its_i64_signature(
        request, tmp_path, compiler):
    ir = _emit(request, compiler, tmp_path, name="r4853lib.ritz")
    assert re.search(r"^define [^\n]*@lib_self_call\(i64 ", ir, re.M), ir
    calls = _calls(ir, "lib_self_call")
    assert calls and all("@lib_self_call(i64 " in c for c in calls), calls
    assert not re.search(r"^declare [^\n]*@lib_self_call\(", ir, re.M), ir


@pytest.mark.parametrize("compiler", COMPILERS)
def test_test_table_platform_hook_calls_match_their_weak_define(
        request, tmp_path, compiler):
    # --test-table defines the platform hooks weak in this .ll (#4648), with
    # `ptr` params: a call of one is typed as that define is (it was an i64
    # call of a `ptr` define before #4853).
    # gvec's generic Vec.set, instantiated here, calls ritz_platform_fatal.
    src = ("import ritzlib.gvec\n\n[[test]]\nfn test_a() -> i32\n"
           "    var v: Vec<i64> = vec_new<i64>()\n"
           "    v.push(1)\n    v.set(0, 2)\n    0\n")
    ir = _emit(request, compiler, tmp_path, src_text=src,
               extra=("--test-table",))
    for hook in ("ritz_platform_fatal",):
        m = re.search(rf"^define weak (\S+) @{hook}\(([^)]*)\)", ir, re.M)
        assert m, ir
        params = [a.split(" ")[0] for a in m.group(2).split(", ")]
        assert not re.search(rf"^declare [^\n]*@{hook}\(", ir, re.M), ir
        calls = _calls(ir, hook)
        assert calls, f"no call of {hook}"
        for call in calls:
            assert f"call {m.group(1)} @{hook}(" in call, call
            args = call[call.index(f"@{hook}(") + len(hook) + 2:].rstrip(")")
            assert [a.split(" ")[0] for a in args.split(", ")] == params, call


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_the_program_runs(ritz1_bin, tmp_path, compiler):
    pkg = tmp_path / f"r4853_{compiler}"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text(RUN_SRC)
    (pkg / "src" / "r4853lib.ritz").write_text(LIB)
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "r4853"\nversion = "0.1.0"\n')
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT),
               RITZ_BUILD_CACHE_DIR=str(pkg / ".build-cache"))
    proc = subprocess.run(
        ["python3", str(RITZ_ROOT / "build.py"), "build", str(pkg),
         "--compiler", compiler],
        cwd=RITZ_ROOT, env=env, capture_output=True, text=True, timeout=600)
    exe = pkg / "build" / "debug" / "r4853"
    assert proc.returncode == 0 and exe.exists(), (
        proc.stdout[-3000:] + proc.stderr[-3000:])
    assert subprocess.run([str(exe)], timeout=60).returncode == 40
