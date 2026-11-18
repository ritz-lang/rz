; Ritz Runtime Entry Point: the one `_start` (docs/V1_ABI_CLEANUP.md, AGAST #200)
;
; Every program is entered here and calls `main(argc, argv, envp)`.
; A C-shaped `main()` / `main(argc, argv)` ignores the registers it does not
; take (SysV); a Ritz-native `pub fn main(args: Span<StrView>, ...)` is reached
; through the adapter `main` the compiler adds (ritz0/main_abi.py,
; ritz1/src/main_abi.ritz), which builds the spans in Ritz.
;
; Stack layout at _start:
;   (%rsp)     = argc
;   8(%rsp)    = argv[0]
;   ...        = argv[1], ..., argv[argc-1], NULL
;   ...        = envp[0], envp[1], ..., NULL
;
; envp = argv + (argc + 1) * 8

target triple = "x86_64-pc-linux-gnu"
target datalayout = ""

; AGAST #3737: the kernel's envp, for ritzlib.os.env. Weak: ritzlib/os/env.ritz
; defines it too (one storage after linking); without os/env this one stands.
@__ritz_envp = weak global i8** null

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
    movq %rdx, __ritz_envp(%rip)
    andq $$-16, %rsp
    call main
    movq %rax, %rdi
    movq $$60, %rax
    syscall
  ", "~{rax},~{rdi},~{rsi},~{rdx},~{rsp},~{rcx},~{r11},~{memory}"()
  unreachable
}
