; Ritz Runtime Entry Point (with args variant)
; For programs with: fn main(argc: i32, argv: **i8) -> i32
;
; Stack layout at _start:
;   (%rsp)     = argc
;   8(%rsp)    = argv[0]
;   ...        = argv[1], ..., argv[argc-1], NULL
;   ...        = envp[0], envp[1], ..., NULL

target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

declare i32 @main(i32 %argc, i8** %argv)

define void @_start() naked {
entry:
  call void asm sideeffect "
    movq (%rsp), %rdi
    leaq 8(%rsp), %rsi
    andq $$-16, %rsp
    call main
    movq %rax, %rdi
    movq $$60, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
