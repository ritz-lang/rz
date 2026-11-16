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

; AGAST #3737: the kernel's envp, for ritzlib.os.env. Weak: ritzlib/os/env.ritz
; defines it too (one storage after linking); without os/env this one stands.
@__ritz_envp = weak global i8** null

declare i32 @main()

define void @_start() naked {
entry:
  call void asm sideeffect "
    movq %rdx, __ritz_envp(%rip)
    andq $$-16, %rsp
    call main
    movq %rax, %rdi
    movq $$20, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rdx},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
