; Ritz Runtime Entry Point for Harland (with args variant)
; For programs with: fn main(argc: i32, argv: **i8) -> i32
;
; Stack layout at _start:
;   (%rsp)     = argc
;   8(%rsp)    = argv[0]
;   ...        = argv[1], ..., argv[argc-1], NULL
;   ...        = envp[0], envp[1], ..., NULL
;
; Harland syscall numbers differ from Linux:
;   SYS_EXIT = 20 (Linux uses 60)

target triple = "x86_64-unknown-none"
target datalayout = ""

declare i32 @main(i32 %argc, i8** %argv)

define void @_start() naked {
entry:
  call void asm sideeffect "
    movq (%rsp), %rdi
    leaq 8(%rsp), %rsi
    andq $$-16, %rsp
    subq $$8, %rsp
    call main
    movq %rax, %rdi
    movq $$20, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
