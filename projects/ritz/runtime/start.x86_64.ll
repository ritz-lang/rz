; Ritz Unified Runtime Entry Point — Linux x86_64
;
; Single canonical _start that always extracts argc/argv/envp from the kernel's
; stack layout and hands off to ritz_start (a Ritz function in ritzlib.entry).
;
; Replaces the three legacy shims:
;   ritz_start.x86_64.ll          (main(argc, argv))
;   ritz_start_envp.x86_64.ll     (main(argc, argv, envp))
;   ritz_start_noargs.x86_64.ll   (main())
;
; Stack layout at _start (Linux x86_64 SysV ABI):
;   (%rsp)     = argc
;   8(%rsp)    = argv[0]
;   ...        = argv[1], ..., argv[argc-1], NULL
;   ...        = envp[0], envp[1], ..., NULL
;
; envp = argv + (argc + 1) * 8
;
; The Ritz-side entry function is responsible for:
;   - building Span<StrView> for argv (and optionally envp)
;   - calling the user's main with the right shape
;   - calling sys_exit with the return code
;
; If ritz_start ever returns (which it shouldn't), we fall through to a defensive
; sys_exit(rc) so a bug in ritz_start doesn't leave us trapping.

target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

declare i32 @ritz_start(i32 %argc, i8** %argv, i8** %envp)

define void @_start() naked {
entry:
  call void asm sideeffect "
    movq (%rsp), %rdi
    leaq 8(%rsp), %rsi
    movq %rdi, %rax
    addq $$1, %rax
    shlq $$3, %rax
    leaq 8(%rsp,%rax), %rdx
    andq $$-16, %rsp
    call ritz_start
    movq %rax, %rdi
    movq $$60, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rdx},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
