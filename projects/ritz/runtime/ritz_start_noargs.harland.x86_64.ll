; Ritz Runtime Entry Point for Harland (no-args variant)
; For programs with: fn main() -> i32
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

declare i32 @main()

define void @_start() naked {
entry:
  call void asm sideeffect "
    andq $$-16, %rsp
    call main
    movq %rax, %rdi
    movq $$20, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
