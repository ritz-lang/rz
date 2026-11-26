# UEFI Entry Point Assembly
#
# UEFI uses Microsoft x64 ABI: RCX, RDX, R8, R9
#
# When compiling with --target=x86_64-unknown-windows, clang uses MS x64 ABI
# for all functions, so our Ritz code expects args in RCX, RDX too!
#
# This entry point is minimal - just add shadow space and call efi_main.

.code64

.section .text
.global _start
.extern efi_main

_start:
    # UEFI passes (Microsoft x64 ABI):
    #   RCX = ImageHandle
    #   RDX = SystemTable
    #
    # efi_main also expects MS x64 ABI (compiled with Windows target)
    # so no conversion needed!

    # Save callee-saved registers (MS x64 requires RBX, RBP, RDI, RSI, R12-R15)
    pushq %rbx
    pushq %rbp
    pushq %rdi
    pushq %rsi
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15

    # Add shadow space for MS x64 ABI (32 bytes minimum)
    subq $32, %rsp

    # Call efi_main(image_handle, system_table)
    # Args already in RCX, RDX - no conversion needed!
    call efi_main

    # Restore stack
    addq $32, %rsp

    # Restore callee-saved registers
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rsi
    popq %rdi
    popq %rbp
    popq %rbx

    # Return to UEFI (result in RAX)
    ret
