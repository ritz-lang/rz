; Ritz Runtime Entry Point for Harland (with args variant)
; For programs with: fn main(argc: i32, argv: **i8) -> i32
;
; Register layout at _start (passed by Harland kernel):
;   RDI = argc
;   RSI = argv (pointer to array of string pointers)
;
; This differs from Linux where argc/argv are on the stack.
; The kernel's jump_to_userspace_with_args passes them in registers.
;
; Harland syscall numbers differ from Linux:
;   SYS_EXIT = 20 (Linux uses 60)

target triple = "x86_64-unknown-none"
target datalayout = ""

declare i32 @main(i32 %argc, i8** %argv)

define void @_start() naked {
entry:
  call void asm sideeffect "
    # argc is already in RDI, argv is already in RSI
    # Just align the stack and call main
    andq $$-16, %rsp
    subq $$8, %rsp
    call main
    movq %rax, %rdi
    movq $$20, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
