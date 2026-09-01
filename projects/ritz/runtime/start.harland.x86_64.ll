; Ritz Unified Runtime Entry Point — Harland x86_64
;
; Single canonical _start for Harland userspace processes. The kernel's
; jump_to_userspace_with_args passes argc/argv in registers (RDI/RSI), not on
; the stack.
;
; Harland does not currently expose envp at the kernel boundary, so we pass
; NULL — Ritz-side ritz_start translates that into an empty Span<StrView> and
; ritzlib.os.env will fail-soft on lookups (returning Option::none()).

target triple = "x86_64-unknown-none"
target datalayout = ""

declare i32 @ritz_start(i32 %argc, i8** %argv, i8** %envp)

define void @_start() naked {
entry:
  call void asm sideeffect "
    xorq %rdx, %rdx
    andq $$-16, %rsp
    subq $$8, %rsp
    call ritz_start
    movq %rax, %rdi
    movq $$20, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rdx},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
