; Ritz Runtime Entry Point (no-args variant)
; For programs with: fn main() -> i32
;
; Stack layout at _start:
;   (%rsp)     = argc
;   8(%rsp)    = argv[0]
;   ...        = argv[1], ..., argv[argc-1], NULL
;   ...        = envp[0], envp[1], ..., NULL

target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

declare i32 @main()

define void @_start() naked {
entry:
  call void asm sideeffect "
    andq $$-16, %rsp
    call main
    movq %rax, %rdi
    movq $$60, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
