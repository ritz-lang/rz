; Ritz Runtime Entry Point for Harland: the one `_start` there
; (docs/V1_ABI_CLEANUP.md, AGAST #200). It calls `main(argc, argv, envp)`,
; as runtime/ritz_start.x86_64.ll does on Linux.
;
; Register layout at _start (passed by Harland kernel):
;   RDI = argc
;   RSI = argv (pointer to array of string pointers)
;   RDX = envp (may be NULL on Harland)
;
; This differs from Linux where argc/argv are on the stack.
; The kernel's jump_to_userspace_with_args passes them in registers.
;
; Harland syscall numbers differ from Linux:
;   SYS_EXIT = 20 (Linux uses 60)

target triple = "x86_64-unknown-none"
target datalayout = ""

; AGAST #3737: the kernel's envp, for ritzlib.os.env. Weak: ritzlib/os/env.ritz
; defines it too (one storage after linking); without os/env this one stands.
@__ritz_envp = weak global i8** null

declare i32 @main(i32 %argc, i8** %argv, i8** %envp)

; No alignstack(16) "no-builtins" (AGAST #1326): the body is one asm block,
; so loop-idiom has no loop to rewrite and there is no prologue to align.
define void @_start() naked {
entry:
  call void asm sideeffect "
    # argc, argv and envp are already in RDI, RSI and RDX. The stack is
    # 16-aligned at the call, as the SysV ABI wants and as the Linux shim
    # does (the old two-arg Harland shim left it 8 off).
    movq %rdx, __ritz_envp(%rip)
    andq $$-16, %rsp
    call main
    movq %rax, %rdi
    movq $$20, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rdx},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
