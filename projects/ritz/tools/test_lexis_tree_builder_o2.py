"""lexis tree_builder.ritz compiles to an object at -O2 within bound (AGAST #3689).

THE DEFECT

Five read-only helpers in lexis/lib/html/tree_builder.ritz took
`tb: TreeBuilder` by value. TreeBuilder is ~22 KB: `[512]StackEntry`,
`[128]FormattingEntry` and a 4 KB text buffer. A by-value param that size is
`ptr byval(%TreeBuilder)`, so each call copies 22 KB. Most callers hold
`tb:& TreeBuilder`. In `process_end_tag_in_body`, building the second arg
(`Tag.Body`) stores into an alloca between the load of `tb` and the call. That
store stops ritz0's pointer-to-pointer copy (#1732/#1739), so ritz0 falls
back to a first-class `load`/`store %TreeBuilder`. SROA splits that into
~179k instructions, then InstCombine stalls on them. Measured on clang 20.1.8
for the emitted .ll:

    -O0  4.5 s     -O1  >120 s     -O2  >300 s (RITZ_CLANG_OBJ_TIMEOUT)

With the copies rewritten to @__ritz_sret_copy, -O2 takes 1.0 s.

THE FIX

The helpers take `tb: @TreeBuilder`, so no call copies the struct. ritz0
still has the fallback, and a ticket tracks fixing it there.

The IR and -O2 tests need ritz0 to accept tree_builder.ritz. Until the Tag
`==` sites are gone (#2213), ritz0 rejects the file and these tests skip with
that reason. They run once #2213 lands.
"""

import json
import re
import resource
import subprocess
import sys
import time
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
PROJECTS = RITZ_ROOT.parent
LEXIS = PROJECTS / "lexis"
TREE_BUILDER = LEXIS / "lib" / "html" / "tree_builder.ritz"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"

# A healthy compile takes about 1 s. The defect ran past 300 s.
O2_BOUND_S = 60
CLANG_MEM_BYTES = 4096 * 1024 * 1024

# #2213 removes these. Until then ritz0 rejects the file before codegen.
TAG_EQ_PENDING = "'==' is not supported for struct type 'enum.ritz_module_1.Tag'"

# `name: TreeBuilder`. A `name:& TreeBuilder` or `name: @TreeBuilder` param
# does not match.
BY_VALUE_PARAM = re.compile(r"\b\w+\s*:\s*TreeBuilder\b")
FN_SIG = re.compile(r"^\s*(?:pub\s+)?fn\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)

TB_T = r'%"?(?:struct\.[\w.]*\.)?TreeBuilder"?'
FIRST_CLASS_TB = re.compile(rf"(?:= load {TB_T},|store {TB_T} )")


def test_no_fn_takes_tree_builder_by_value():
    text = TREE_BUILDER.read_text()
    by_value = [name for name, params in FN_SIG.findall(text)
                if BY_VALUE_PARAM.search(params)]
    assert by_value == [], (
        f"these fns copy the ~22 KB TreeBuilder on every call; take "
        f"`tb: @TreeBuilder` (or `tb:& TreeBuilder`) instead: {by_value}")


@pytest.fixture(scope="module")
def tree_builder_ll(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("lexis_tb") / "tree_builder.ll"
    deps = {
        "ritzlib": {"path": str(RITZ_ROOT / "ritzlib"), "sources": ["."]},
        "ritzunit": {"path": str(PROJECTS / "ritzunit"), "sources": ["."]},
    }
    r = subprocess.run(
        [sys.executable, str(RITZ0), str(TREE_BUILDER), "-o", str(out),
         "--no-runtime", "--deps", json.dumps(deps),
         "--sources", json.dumps(["lib", "src"]),
         "--project-root", str(LEXIS)],
        capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        err = r.stdout + r.stderr
        if TAG_EQ_PENDING in err:
            pytest.skip("ritz0 rejects tree_builder.ritz until the Tag `==` "
                        "sites are gone (#2213)")
        pytest.fail(f"ritz0 failed on tree_builder.ritz:\n{err[-3000:]}")
    return out


@pytest.mark.integration
def test_tree_builder_ll_has_no_first_class_tree_builder(tree_builder_ll):
    bad = [line.strip()[:160] for line in tree_builder_ll.read_text().splitlines()
           if FIRST_CLASS_TB.search(line)]
    assert bad == [], ("first-class %TreeBuilder load/store; clang -O2 "
                       "stalls in SROA/InstCombine on these:\n" + "\n".join(bad))


def _cap_address_space():
    resource.setrlimit(resource.RLIMIT_AS, (CLANG_MEM_BYTES, CLANG_MEM_BYTES))


@pytest.mark.integration
def test_tree_builder_compiles_at_O2_within_bound(tree_builder_ll):
    obj = tree_builder_ll.with_suffix(".o")
    start = time.monotonic()
    try:
        r = subprocess.run(
            ["clang", "-c", "-O2", "-fPIC", "-ffreestanding", "-fno-builtin",
             "-Wno-override-module", str(tree_builder_ll), "-o", str(obj)],
            capture_output=True, text=True, timeout=O2_BOUND_S,
            preexec_fn=_cap_address_space)
    except subprocess.TimeoutExpired:
        pytest.fail(f"clang -c -O2 on tree_builder.ll ran past {O2_BOUND_S}s")
    elapsed = time.monotonic() - start
    assert r.returncode == 0, r.stderr[-3000:]
    assert obj.exists()
    assert elapsed < O2_BOUND_S
