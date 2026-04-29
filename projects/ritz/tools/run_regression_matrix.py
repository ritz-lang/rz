#!/usr/bin/env python3
"""
Matrix runner for the 33 test_issue_*.ritz tests across 3 compilers.
Run: python3 projects/ritz/tools/run_regression_matrix.py [--tests REGEX] [--compiler all|ritz0|ritz1|ritz1_selfhosted] [-v]
"""

import argparse, os, re, signal, subprocess, sys, tempfile
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

RITZLIB_MODULES = ["sys", "io", "str", "strview", "string", "hash", "memory",
                   "gvec", "drop", "env", "option", "result", "hashmap",
                   "bytes", "span"]

TESTS = [
    "test_issue_addr_of_struct_array_member",
    "test_issue_array_fill_literal",
    "test_issue_chained_deref_fwd_field",
    "test_issue_array_value_to_span",
    "test_issue_binop_as_cast",
    "test_issue_call_mut_ref_to_ref_coerce",
    "test_issue_const_struct_array",
    "test_issue_const_strview_array",
    "test_issue_float_coercion",
    "test_issue_fn_ptr_param_autoborrow",
    "test_issue_fn_ref_param_rvalue",
    "test_issue_for_iterables",
    "test_issue_for_range_wrapped",
    "test_issue_generic_call_resolution",
    "test_issue_global_struct_assign",
    "test_issue_inline_asm_cpuid",
    "test_issue_match_custom_87",
    "test_issue_match_option_u32",
    "test_issue_match_pass_arm",
    "test_issue_method_autoborrow_rvalue",
    "test_issue_method_nonself_ptr_arg",
    "test_issue_mut_ref_deref_assign",
    "test_issue_namespace_const_field",
    "test_issue_newtype_int_arg",
    "test_issue_newtype_struct_deref",
    "test_issue_option_return",
    "test_issue_option_unwrap_or_method",
    "test_issue_pass_expr",
    "test_issue_ptr_param_forward",
    "test_issue_ptr_value_coercion",
    "test_issue_qualified_enum_variant",
    "test_issue_result_unwrap_method",
    "test_issue_sizeof_primitive",
    "test_issue_span_slice_range",
    "test_issue_struct_destructure",
    "test_issue_strview_as_bytes",
    "test_issue_try_call",
    "test_issue_try_vec_payload_call",
    "test_issue_usize_suffix_fallback",
    "test_issue_vec_borrow_to_span",
    "test_issue_vec_field_index",
    "test_issue_vec_index_nonident",
    "test_issue_vec_push_u16_method",
]


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


def find_test_fns(src):
    names = []
    lines = src.split("\n")
    i = 0
    while i < len(lines):
        if "[[test]]" in lines[i]:
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines):
                m = re.match(r"^fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", lines[j])
                if m:
                    names.append(m.group(1))
            i = j
        i += 1
    return names


def compile_with_ritz0(src_path, out_ll, env):
    cmd = RITZ0 + [str(src_path), "-o", str(out_ll), "--no-runtime",
                   "--project-root", RITZ_PATH_ENV]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)


def compile_with_ritz1(binary, src_path, out_ll, env):
    cmd = [binary, str(src_path), "-o", str(out_ll)]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)


def build_ritzlib_objs(tmpdir, env):
    objs = []
    for mod in RITZLIB_MODULES:
        src = RITZ_ROOT / "ritzlib" / f"{mod}.ritz"
        if not src.exists():
            continue
        ll = Path(tmpdir) / f"ritzlib_{mod}.ll"
        o = Path(tmpdir) / f"ritzlib_{mod}.o"
        cmd = RITZ0 + [str(src), "-o", str(ll), "--no-runtime",
                       "--project-root", RITZ_PATH_ENV]
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
        if r.returncode != 0:
            return None, f"ritzlib {mod} compile failed: {r.stderr[-300:]}"
        cmd = ["clang", "-c", "-O2", str(ll), "-o", str(o)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return None, f"ritzlib {mod} asm failed: {r.stderr[-300:]}"
        objs.append(str(o))
    return objs, None


def run_one(test_name, compiler_name, compiler_bin, ritzlib_objs, env, tmpdir):
    src_path = TEST_DIR / f"{test_name}.ritz"
    src = src_path.read_text()
    fns = find_test_fns(src)
    if not fns:
        return ("no-test-fn", 0, f"no [[test]] fn in {test_name}")
    src_no_main = strip_main(src)
    harness = src_no_main + f"\n\nfn main() -> i32\n  {fns[0]}()\n"
    wrap = Path(tmpdir) / f"{test_name}_{compiler_name}.ritz"
    wrap.write_text(harness)

    out_ll = Path(tmpdir) / f"{test_name}_{compiler_name}.ll"
    if compiler_name == "ritz0":
        r = compile_with_ritz0(wrap, out_ll, env)
    else:
        r = compile_with_ritz1(compiler_bin, wrap, out_ll, env)
    if r.returncode != 0:
        return ("compile-fail", r.returncode, r.stderr[-400:])

    obj = Path(tmpdir) / f"{test_name}_{compiler_name}.o"
    r = subprocess.run(["clang", "-c", "-O2", str(out_ll), "-o", str(obj)],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return ("asm-fail", r.returncode, r.stderr[-400:])

    exe = Path(tmpdir) / f"{test_name}_{compiler_name}.exe"
    link_cmd = (["ld", "-dynamic-linker", "/lib64/ld-linux-x86-64.so.2", "-lc",
                 "-o", str(exe), str(RUNTIME_O)]
                + ritzlib_objs + [str(obj)])
    r = subprocess.run(link_cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return ("link-fail", r.returncode, r.stderr[-400:])

    try:
        r = subprocess.run([str(exe)], capture_output=True, timeout=10)
    except subprocess.TimeoutExpired:
        return ("timeout", 124, "timeout")
    exit_code = r.returncode
    if exit_code < 0:
        sig = -exit_code
        try:
            name = signal.Signals(sig).name
        except ValueError:
            name = f"SIG{sig}"
        return ("signal", exit_code, name)
    if exit_code == 0:
        return ("pass", 0, "")
    return ("bad-exit", exit_code, "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", default=".*")
    ap.add_argument("--compiler", default="all",
                    choices=["all", "ritz0", "ritz1", "ritz1_selfhosted"])
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
    tests = [t for t in TESTS if test_re.search(t)]

    with tempfile.TemporaryDirectory(prefix="matrix_") as tmpdir:
        print(f"# Building ritzlib objects in {tmpdir} ...", flush=True)
        ritzlib_objs, err = build_ritzlib_objs(tmpdir, env)
        if err:
            print(f"FATAL: {err}")
            return 2

        results = {c: {} for c, _ in compilers}
        for test_name in tests:
            for cname, cbin in compilers:
                status, code, info = run_one(test_name, cname, cbin,
                                             ritzlib_objs, env, tmpdir)
                results[cname][test_name] = (status, code, info)
                tag = "OK" if status == "pass" else "FAIL"
                suffix = ""
                if status != "pass":
                    suffix = f" [{status}"
                    if info and args.verbose:
                        suffix += f": {info[:120]}"
                    suffix += "]"
                print(f"  {cname:20s} {test_name:45s} {tag}{suffix}", flush=True)

        print("\n=== Summary ===")
        for cname, _ in compilers:
            passed = sum(1 for r in results[cname].values() if r[0] == "pass")
            total = len(results[cname])
            print(f"  {cname:20s} {passed}/{total}")

        print("\n=== Failures by compiler ===")
        for cname, _ in compilers:
            fails = [(t, r) for t, r in results[cname].items() if r[0] != "pass"]
            if not fails:
                continue
            print(f"\n-- {cname} ({len(fails)} failures) --")
            for t, (status, code, info) in fails:
                print(f"  {t}: {status} (code={code}) {info[:120]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
