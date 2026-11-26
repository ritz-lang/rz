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

; AGAST #4119: ritzlib's core (memory, hashmap) declares these platform hooks
; instead of importing ritzlib.sys, so it builds freestanding. ritzlib.sys
; defines them; these weak copies stand when a program imports no hosted
; module and so never links sys. Same as sys's: anonymous mmap/munmap (9, 11,
; PROT_READ|PROT_WRITE = 3, MAP_PRIVATE|MAP_ANONYMOUS = 0x22, the same on
; Harland), and msg plus a newline on stderr, then exit(20).
define weak i8* @ritz_platform_page_map(i64 %len) {
entry:
  %r = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},{rsi},{rdx},{r10},{r8},{r9},~{rcx},~{r11},~{memory}"(i64 9, i64 0, i64 %len, i64 3, i64 34, i64 -1, i64 0)
  %p = inttoptr i64 %r to i8*
  ret i8* %p
}

define weak i32 @ritz_platform_page_unmap(i8* %p, i64 %len) {
entry:
  %a = ptrtoint i8* %p to i64
  %r = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},{rsi},~{rcx},~{r11},~{memory}"(i64 11, i64 %a, i64 %len)
  %t = trunc i64 %r to i32
  ret i32 %t
}

@__ritz_platform_nl = private constant [1 x i8] c"\0A"

define weak void @ritz_platform_fatal(i8* %msg, i64 %len, i32 %status) {
entry:
  %m = ptrtoint i8* %msg to i64
  %w1 = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 2, i64 %m, i64 %len)
  %nl = ptrtoint [1 x i8]* @__ritz_platform_nl to i64
  %w2 = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 2, i64 %nl, i64 1)
  %s = sext i32 %status to i64
  %x = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},~{rcx},~{r11},~{memory}"(i64 20, i64 %s)
  unreachable
}
