"""netd blocks only in DrvIrqWait (AGAST #4746, #4875).

RING_DESIGN_FINAL_REVIEW.md "Final pass" item 15: a kernel-spawned network
process parks in exactly one place, its own wait set. Under D9 (#4875,
docs/RING2_NET.md "Drivers inside netd (D9)") the virtio-net driver is a
library inside /bin/netd, which holds the NIC's IRQ capability: its one
wait is DrvIrqWait (220), the IRQ and the app exchanges together, and
ShmWait (229) in netd is a failure like any other blocking call. That is
what keeps PROC_REAP complete: a process parked in its wait set is woken by
endpoint_fail / driver_quiesce, and a process blocked anywhere else (read,
wait, ipc_recv, ShmWait beside its real wait, ...) would not be.

The lint is a source scan, so it reads the code as it is built, not a
pinned call list (netd keeps growing):

* it follows every `import` from the entry module transitively, through the
  harland packages (system, nic, driver_abi, virtio_abi, netstack, ...) and
  ritzlib, resolving each package's namespaces from its own ritz.toml;
* every function in a harland module of that closure is a root (dead code
  counts: it is one call away from live), and a function becomes reachable
  in ritzlib when a reachable body names it, so ritzlib.sys's sys_read is
  reached by a call to sys_read, not by `import ritzlib.sys` alone;
* each reachable `syscallN(nr, ...)` has its number resolved (a literal or a
  harland-gated const) and mapped onto the kernel's `enum Syscall: u64`; it
  must be one of ALLOWED. An unresolvable number, or an `asm` block issuing
  `syscall` outside ritzlib.sys's syscall0..6, fails too.

The proof tests inject a sys_read, a sys_wait, a ShmWait and a raw Wait into
the real sources (netd, the nic library, and netstack two imports away) and
check each is named.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from resolve import package_import_namespaces, read_manifest  # noqa: E402

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
RITZLIB = RITZ_ROOT / "ritzlib"
HARLAND = RITZ_ROOT.parent / "harland"
SYSTEM_SRC = HARLAND / "system" / "src"
NUMBERS = HARLAND / "kernel" / "src" / "syscall" / "numbers.ritz"

NIC_SRC = HARLAND / "nic" / "src"

ENTRIES = {
    "netd": SYSTEM_SRC / "netd.ritz",
}

# The wait: the binary's only place to park.
BLOCKING = {"netd": "DrvIrqWait"}

# Syscalls that return without parking the caller: the ticket's set (Yield,
# ShmNotify, map/alloc, NetPublish, Exit) plus NetInfo (a snapshot copy) and
# CapRevoke (drops a handle) that netd uses on its exit and boot paths. Yield
# is runnable-to-runnable, not a block. Yield, DrvMmioMap, DrvDmaAlloc and
# DrvDmaFree are netd's since D9 (#4875): it brings the NIC up itself.
NON_BLOCKING = {
    "Yield", "ShmNotify", "ShmMap", "DrvMmioMap", "DrvDmaAlloc", "DrvDmaFree",
    "Mmap", "Munmap", "NetPublish", "NetInfo", "CapRevoke", "Exit",
}
ALLOWED = NON_BLOCKING | {"DrvIrqWait"}

SYSCALL_CALL = re.compile(r"\bsyscall([0-6])\s*\(\s*([^,)]+?)\s*[,)]")
IDENT = re.compile(r"\b[A-Za-z_]\w*\b")
FN_DEF = re.compile(r"^(\s*)(?:pub\s+)?fn\s+(\w+)\s*[(<\[]")
CONST_DEF = re.compile(r"^(?:pub\s+)?const\s+(\w+)\s*:\s*\w+\s*=\s*(.+?)\s*$")
IMPORT = re.compile(r"^import\s+([\w.]+)")
TARGET_OS = re.compile(r'^\[\[target_os\s*=\s*"(\w+)"\]\]')


def kernel_syscalls() -> dict[int, str]:
    """{number: variant} as syscall/numbers.ritz declares `enum Syscall: u64`."""
    src = NUMBERS.read_text()
    m = re.search(r"^pub enum Syscall: u64\n((?:[ \t]+.*\n|[ \t]*\n|#.*\n)+)", src, re.M)
    assert m, "syscall/numbers.ritz has no `pub enum Syscall: u64`"
    return {int(v): k for k, v in re.findall(r"^\s+(\w+)\s*=\s*(\d+)", m.group(1), re.M)}


def _code(line: str) -> str:
    """The line without string literals and its trailing comment."""
    line = re.sub(r'c?"(?:[^"\\]|\\.)*"', '""', line)
    line = re.sub(r"'(?:[^'\\]|\\.)*'", "''", line)
    return line.split("#", 1)[0]


@dataclass
class Fn:
    module: str
    name: str
    line: int
    body: list[tuple[int, str]]


@dataclass
class Module:
    name: str
    path: Path
    harland: bool
    imports: list[str] = field(default_factory=list)
    consts: dict[str, str] = field(default_factory=dict)
    fns: list[Fn] = field(default_factory=list)


def parse_module(name: str, path: Path, text: str) -> Module:
    """Imports, harland-visible consts and fn bodies (top level and impl)."""
    mod = Module(name, path, harland=not path.is_relative_to(RITZLIB))
    lines = text.splitlines()
    gate = None  # the pending [[target_os]] of the next item
    i = 0
    while i < len(lines):
        raw = lines[i]
        code = _code(raw).rstrip()
        stripped = code.strip()
        i += 1
        if not stripped:
            continue
        # Attributes match on the raw line: _code blanks their "strings".
        t = TARGET_OS.match(raw.strip())
        if t:
            gate = t.group(1)
            continue
        if stripped.startswith("[[") and stripped.endswith("]]"):
            continue  # another attribute keeps the pending gate
        visible = gate in (None, "harland")
        gate = None
        if m := IMPORT.match(code):
            mod.imports.append(m.group(1))
            continue
        if m := CONST_DEF.match(code):
            if visible:
                mod.consts[m.group(1)] = m.group(2)
            continue
        if m := FN_DEF.match(code):
            indent = len(m.group(1))
            body = [(i, code)]
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent:
                    break
                body.append((i + 1, _code(nxt)))
                i += 1
            if visible:
                mod.fns.append(Fn(name, m.group(2), body[0][0], body))
    return mod


def _package_dir(path: Path) -> Path:
    for d in path.parents:
        if (d / "ritz.toml").exists():
            return d
    raise AssertionError(f"{path}: no ritz.toml above it")


def resolve_module(name: str, importer: Path) -> Path:
    """The file `import <name>` in `importer` names (ritzlib, or a namespace of
    the importer's package: its [dependencies] and its own name)."""
    head, *rest = name.split(".")
    if head == "ritzlib":
        roots = [RITZLIB]
    else:
        pkg = _package_dir(importer)
        spaces = package_import_namespaces(read_manifest(pkg), pkg)
        assert head in spaces, f"{importer}: `import {name}`: {pkg.name} has no namespace {head}"
        spec = spaces[head]
        roots = [Path(spec.path) / s for s in spec.sources]
    for root in roots:
        cand = root.joinpath(*rest).with_suffix(".ritz")
        if cand.exists():
            return cand.resolve()
    raise AssertionError(f"{importer}: `import {name}` resolves to no file under {roots}")


def load_closure(entry: Path, overrides: dict[Path, str]) -> dict[str, Module]:
    """Every module the entry imports, transitively, keyed by dotted name."""
    entry = entry.resolve()
    mods: dict[str, Module] = {}
    todo = [(f"system.{entry.stem}", entry)]
    seen = set()
    while todo:
        name, path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        mods[name] = mod = parse_module(name, path, overrides.get(path) or path.read_text())
        for imp in mod.imports:
            todo.append((imp, resolve_module(imp, path)))
    return mods


def _resolve_number(expr: str, mod: Module, mods: dict[str, Module]) -> int | None:
    """A syscall number: an integer literal, or a const of the module or of a
    module it imports, followed until it is a literal."""
    for _ in range(8):
        expr = expr.strip()
        if re.fullmatch(r"\d+", expr):
            return int(expr)
        if re.fullmatch(r"0x[0-9a-fA-F]+", expr):
            return int(expr, 16)
        if not re.fullmatch(r"\w+", expr):
            return None
        scopes = [mod] + [mods[i] for i in mod.imports if i in mods]
        found = [m.consts[expr] for m in scopes if expr in m.consts]
        if not found:
            return None
        expr = found[0].split(" as ")[0]
    return None


def _is_raw_primitive(fn: Fn) -> bool:
    return fn.module == "ritzlib.sys" and re.fullmatch(r"syscall[0-6]", fn.name) is not None


def scan(binary: str, overrides: dict[Path, str] | None = None):
    """(violations, reached syscall variants, module names) for one binary."""
    mods = load_closure(ENTRIES[binary], {p.resolve(): t for p, t in (overrides or {}).items()})
    by_name: dict[str, list[Fn]] = {}
    for m in mods.values():
        for fn in m.fns:
            by_name.setdefault(fn.name, []).append(fn)
    numbers = kernel_syscalls()
    reached: list[Fn] = [fn for m in mods.values() if m.harland for fn in m.fns]
    seen = {id(f) for f in reached}
    work = list(reached)
    while work:
        fn = work.pop()
        for _, code in fn.body[1:]:
            for word in IDENT.findall(code):
                for callee in by_name.get(word, ()):
                    if id(callee) not in seen:
                        seen.add(id(callee))
                        reached.append(callee)
                        work.append(callee)
    violations, variants = [], set()
    for fn in reached:
        if _is_raw_primitive(fn):
            continue
        mod = mods[fn.module]
        where = f"{mod.path.relative_to(RITZ_ROOT.parent)}:{fn.name}"
        in_asm = False
        for lineno, code in fn.body[1:]:
            if re.search(r"\basm\b", code):
                in_asm = True
            if in_asm and re.search(r"^\s*(syscall|sysenter|int\s+0x80)\b", code):
                violations.append(f"{where}:{lineno}: raw syscall instruction")
            for m in SYSCALL_CALL.finditer(code):
                n = _resolve_number(m.group(2), mod, mods)
                if n is None:
                    violations.append(f"{where}:{lineno}: syscall number {m.group(2)!r} unresolved")
                    continue
                variant = numbers.get(n, f"#{n}")
                variants.add(variant)
                if variant not in ALLOWED:
                    violations.append(f"{where}:{lineno}: {variant} ({n}) may block")
    return violations, variants, set(mods)


def test_allowed_set_names_kernel_syscalls():
    """Every ALLOWED name is a kernel syscall: a rename can't hollow the lint."""
    variants = set(kernel_syscalls().values())
    assert ALLOWED <= variants, ALLOWED - variants


@pytest.mark.parametrize("binary", sorted(ENTRIES))
def test_binary_blocks_only_in_its_wait(binary):
    violations, variants, _ = scan(binary)
    assert violations == [], "\n".join(violations)
    # Not vacuous: the scan sees the binary's one wait.
    assert BLOCKING[binary] in variants, variants


def test_scan_follows_imports_transitively():
    _, _, mods = scan("netd")
    assert {"system.netd", "system.netsvc", "nic.virtio", "driver_abi.wait", "ritzlib.sys"} <= mods, mods
    assert any(m.startswith("netstack.") for m in mods), mods


def test_the_driver_is_a_library_not_a_binary():
    """D9: /bin/virtio-net is gone; its code is the nic library netd links."""
    assert not (SYSTEM_SRC / "virtio_net.ritz").exists()
    assert (NIC_SRC / "virtio.ritz").exists()


# --- proof: an added blocking call fails --------------------------------------


def _inject(path: Path, fn: str, line: str) -> dict[Path, str]:
    """`path`'s text with a function `fn` holding `line` appended."""
    text = path.read_text()
    return {path: text + f"\nfn {fn}()\n    {line}\n"}


@pytest.mark.parametrize("binary,path,line,variant", [
    ("netd", ENTRIES["netd"], "sys_read(0, null, 0)", "Read"),
    ("netd", NIC_SRC / "virtio.ritz", "sys_wait(1)", "Wait"),
])
def test_added_ritzlib_blocking_call_fails(binary, path, line, variant):
    violations, _, _ = scan(binary, _inject(path, "lint_probe", line))
    assert any(f"{variant} (" in v and "ritzlib/sys.ritz" in v for v in violations), violations


def test_added_shm_wait_in_netd_fails():
    # D9 (#4875): netd's one wait is DrvIrqWait; a ShmWait beside it is a
    # second place to park, named like any other blocking call.
    probe = _inject(ENTRIES["netd"], "lint_probe", "syscall1(229, 0)")
    violations, _, _ = scan("netd", probe)
    assert any("ShmWait (229) may block" in v and "system/src/netd.ritz:lint_probe" in v for v in violations), violations


def test_added_raw_wait_two_imports_away_fails():
    # netd -> system.netsvc -> netstack.*: a raw Wait (22) there is reached.
    _, _, mods = scan("netd")
    netstack = sorted(m for m in mods if m.startswith("netstack."))[0]
    path = resolve_module(netstack, SYSTEM_SRC / "netsvc.ritz")
    probe = _inject(path, "lint_probe", "syscall1(22, 0)")
    violations, _, _ = scan("netd", probe)
    assert any("Wait (22) may block" in v and "netstack" in v for v in violations), violations


def test_unresolved_syscall_number_fails():
    probe = _inject(ENTRIES["netd"], "lint_probe", "syscall1(mystery(), 0)")
    violations, _, _ = scan("netd", probe)
    assert any("unresolved" in v for v in violations), violations


def test_blocking_call_two_ritzlib_hops_away_fails():
    # netd -> ritzlib.str's lint_helper -> ritzlib.sys's sys_wait: the
    # reachability walks ritzlib bodies, not just the names harland calls.
    helper = _inject(RITZLIB / "str.ritz", "lint_helper", "sys_wait(1)")
    probe = _inject(ENTRIES["netd"], "lint_probe", "lint_helper()")
    violations, _, _ = scan("netd", {**helper, **probe})
    assert any("Wait (22) may block" in v and "ritzlib/sys.ritz:sys_wait" in v for v in violations), violations


def test_scan_sees_only_harland_items_of_ritzlib():
    # [[target_os = "linux"]] items are not in a harland build: SYS_EXIT is
    # harland's 20 (Linux's is 60), and sys_open is the harland one only.
    mod = parse_module("ritzlib.sys", RITZLIB / "sys.ritz", (RITZLIB / "sys.ritz").read_text())
    assert mod.consts["SYS_EXIT"] == "20"
    assert len([f for f in mod.fns if f.name == "sys_open"]) == 1
