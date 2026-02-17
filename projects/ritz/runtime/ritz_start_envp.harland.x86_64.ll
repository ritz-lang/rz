; Ritz Runtime Entry Point for Harland (with args and envp variant)
; For programs with: fn main(argc: i32, argv: **i8, envp: **i8) -> i32
;
; Register layout at _start (passed by Harland kernel):
;   RDI = argc
;   RSI = argv (pointer to array of string pointers)
;   RDX = envp (pointer to environment, may be NULL on Harland)
;
; This differs from Linux where argc/argv/envp are on the stack.
; The kernel's jump_to_userspace_with_args passes them in registers.
;
; Harland syscall numbers differ from Linux:
;   SYS_EXIT = 20 (Linux uses 60)

target triple = "x86_64-unknown-none"
target datalayout = ""

declare i32 @main(i32 %argc, i8** %argv, i8** %envp)

define void @_start() naked {
entry:
  call void asm sideeffect "
    # argc is already in RDI, argv is already in RSI
    # envp would be in RDX (currently NULL on Harland)
    # Just align the stack and call main
    andq $$-16, %rsp
    subq $$8, %rsp
    call main
    movq %rax, %rdi
    movq $$20, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rdx},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
