; Ritz Runtime Entry Point for Harland (with args and envp variant)
; For programs with: fn main(argc: i32, argv: **i8, envp: **i8) -> i32
;
; Stack layout at _start:
;   (%rsp)     = argc
;   8(%rsp)    = argv[0]
;   ...        = argv[1], ..., argv[argc-1], NULL
;   ...        = envp[0], envp[1], ..., NULL
;
; envp = argv + (argc + 1) * 8
;
; Harland syscall numbers differ from Linux:
;   SYS_EXIT = 20 (Linux uses 60)

target triple = "x86_64-unknown-none"
target datalayout = ""

declare i32 @main(i32 %argc, i8** %argv, i8** %envp)

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
    subq $$8, %rsp
    call main
    movq %rax, %rdi
    movq $$20, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rdx},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
