"""`alloca T, <ty> %n`: an alloca whose element count is a value
(../razm/DESIGN.md "LLVM IR subset", Memory).

ritz1's `__ritz_match_trap` (AGAST #4586) sizes its message buffer at run
time, and the harland build of buddhafinger reached rllvm with it (#4808).
The block lives below the fixed frame: `%rsp` moves down at the alloca and
stays there, so a later call, even one with stack arguments, must not reset
`%rsp` over it, and each call still starts 16-aligned.
"""

from __future__ import annotations

from test_intrinsics import run_both

# @fill writes n slots in a run-time block, calls a function with stack
# arguments (rllvm's outgoing-area path) and one that dirties its own frame,
# then sums the block: a block the calls overwrote sums wrong. @align_at
# reports %rsp mod 16 at a callee's entry. [3 x i8] takes the multiply.
IR = r"""
declare void @rt_hex(...)

define internal i64 @eight(i64 %a, i64 %b, i64 %c, i64 %d, i64 %e, i64 %f, i64 %g, i64 %h) {
entry:
  %s = add i64 %g, %h
  ret i64 %s
}

define internal void @smash() {
entry:
  %junk = alloca [64 x i64]
  br label %w
w:
  %k = phi i64 [ 0, %entry ], [ %k1, %w ]
  %p = getelementptr i64, ptr %junk, i64 %k
  store volatile i64 -1, ptr %p
  %k1 = add i64 %k, 1
  %go = icmp ult i64 %k1, 64
  br i1 %go, label %w, label %done
done:
  ret void
}

define internal i64 @align_at() {
entry:
  %sp = call i64 asm sideeffect "movq %rsp, $0", "=r,~{memory}"()
  %m = and i64 %sp, 15
  ret i64 %m
}

define internal i64 @fill(i64 %n) {
entry:
  %buf = alloca i64, i64 %n
  br label %put
put:
  %i = phi i64 [ 0, %entry ], [ %i1, %put ]
  %slot = getelementptr i64, ptr %buf, i64 %i
  %v = mul i64 %i, 3
  store i64 %v, ptr %slot
  %i1 = add i64 %i, 1
  %more = icmp ult i64 %i1, %n
  br i1 %more, label %put, label %calls
calls:
  %e = call i64 @eight(i64 1, i64 2, i64 3, i64 4, i64 5, i64 6, i64 7, i64 8)
  call void @smash()
  %odd = alloca [3 x i8], i32 5
  store i8 9, ptr %odd
  %al = call i64 @align_at()
  call void (...) @rt_hex(i64 %al)
  br label %sum
sum:
  %j = phi i64 [ 0, %calls ], [ %j1, %sum ]
  %acc = phi i64 [ %e, %calls ], [ %acc1, %sum ]
  %at = getelementptr i64, ptr %buf, i64 %j
  %x = load i64, ptr %at
  %acc1 = add i64 %acc, %x
  %j1 = add i64 %j, 1
  %again = icmp ult i64 %j1, %n
  br i1 %again, label %sum, label %out
out:
  %o = load i8, ptr %odd
  %oz = zext i8 %o to i64
  %r = add i64 %acc1, %oz
  ret i64 %r
}

define i32 @main() {
entry:
  %a = call i64 @fill(i64 7)
  call void (...) @rt_hex(i64 %a)
  %b = call i64 @fill(i64 1)
  call void (...) @rt_hex(i64 %b)
  ret i32 0
}
"""


def test_dynamic_alloca_survives_calls_and_runs_as_clang(rllvm_bin, tmp_path):
    oracle, ours = run_both(rllvm_bin, tmp_path, IR)
    # 7 slots: 3*(0+..+6) = 63, + 7 + 8 from @eight, + 9 = 87 (0x57).
    assert oracle.status == 0 and b"57" in oracle.stdout
    assert ours == oracle
