# Syscall Entry/Exit Assembly (x86_64)
#
# Fast system call entry point using SYSCALL instruction.
#
# On SYSCALL entry (set by CPU):
#   RCX = return RIP
#   R11 = saved RFLAGS
#   Interrupts may be disabled (depends on SFMASK)
#
# Syscall ABI:
#   RAX = syscall number
#   RDI = arg1, RSI = arg2, RDX = arg3
#   R10 = arg4 (RCX is clobbered), R8 = arg5, R9 = arg6
#
# Return value in RAX

.section .data
# Kernel stack for syscall handling (4KB per CPU - TODO: per-CPU)
.align 16
syscall_stack:
    .space 4096
syscall_stack_top:

# Saved user RSP during syscall
user_rsp_save:
    .quad 0

# ============================================================================
# Exported User Context (for spawn/exit)
# ============================================================================
# These globals are updated on syscall entry and can be read/written by
# the syscall handler to implement spawn (save parent) and exit (restore parent).

.global syscall_user_rip
.global syscall_user_rsp
.global syscall_user_rflags

syscall_user_rip:
    .quad 0
syscall_user_rsp:
    .quad 0
syscall_user_rflags:
    .quad 0
syscall_user_rax:
    .quad 0

.section .text

# ============================================================================
# User Context Accessor Functions
# ============================================================================
# These functions allow Ritz code to read the saved user context.

.global get_syscall_user_rip
.type get_syscall_user_rip, @function
get_syscall_user_rip:
    movq syscall_user_rip(%rip), %rax
    ret
.size get_syscall_user_rip, . - get_syscall_user_rip

.global get_syscall_user_rsp
.type get_syscall_user_rsp, @function
get_syscall_user_rsp:
    movq syscall_user_rsp(%rip), %rax
    ret
.size get_syscall_user_rsp, . - get_syscall_user_rsp

.global get_syscall_user_rflags
.type get_syscall_user_rflags, @function
get_syscall_user_rflags:
    movq syscall_user_rflags(%rip), %rax
    ret
.size get_syscall_user_rflags, . - get_syscall_user_rflags

.section .text

# ============================================================================
# Syscall Entry Point
# ============================================================================
.global syscall_entry
.type syscall_entry, @function
syscall_entry:
    # At this point:
    #   - We're in Ring 0
    #   - RCX = user RIP (return address)
    #   - R11 = user RFLAGS
    #   - RSP = user stack (NOT safe to use yet!)
    #   - RAX = syscall number
    #   - Interrupts are disabled (SFMASK clears IF)

    # CRITICAL: Switch to kernel stack immediately
    # Save user RSP first
    movq %rsp, user_rsp_save(%rip)

    # Load kernel syscall stack
    leaq syscall_stack_top(%rip), %rsp

    # Now we have a safe kernel stack

    # Save RAX (syscall number) to global FIRST before using it as scratch
    # This is critical - we were clobbering it before!
    movq %rax, syscall_user_rax(%rip)      # Save syscall number

    # Export user context to globals (for spawn/exit to access)
    movq %rcx, syscall_user_rip(%rip)      # User return RIP
    movq user_rsp_save(%rip), %rax         # Use RAX as scratch now (already saved)
    movq %rax, syscall_user_rsp(%rip)      # User RSP
    movq %r11, syscall_user_rflags(%rip)   # User RFLAGS

    # Restore RAX from saved value before pushing to frame
    movq syscall_user_rax(%rip), %rax

    # Save all registers that the syscall handler might need
    # Build a SyscallFrame on the stack
    pushq user_rsp_save(%rip)   # user_rsp
    pushq %r11                   # saved RFLAGS
    pushq %rcx                   # return RIP
    pushq %r9                    # arg6
    pushq %r8                    # arg5
    pushq %r10                   # arg4
    pushq %rdx                   # arg3
    pushq %rsi                   # arg2
    pushq %rdi                   # arg1
    pushq %rax                   # syscall number

    # Also save callee-saved registers (in case handler uses them)
    pushq %rbx
    pushq %rbp
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15

    # Enable interrupts during syscall handling
    # This is safe because we're on the dedicated syscall_stack.
    # IRQs use IST=0 (current stack), so they push onto syscall_stack.
    # Userspace runs with IF=0, so timer only fires during syscall.
    sti

    # Call the Ritz syscall handler
    # syscall_handler(rax, rdi, rsi, rdx) -> i64
    #
    # Our saved frame on the stack (after callee-saved):
    #   +0:  RAX (syscall number)
    #   +8:  RDI (arg1)
    #   +16: RSI (arg2)
    #   +24: RDX (arg3)
    #   ... etc
    #
    # Load arguments from saved frame
    movq 48(%rsp), %rdi          # rdi = saved RAX (syscall number)
    movq 56(%rsp), %rsi          # rsi = saved RDI (arg1)
    movq 64(%rsp), %rdx          # rdx = saved RSI (arg2)
    movq 72(%rsp), %rcx          # rcx = saved RDX (arg3)
    call syscall_handler

    # Return value is in RAX - save it to a temporary location
    # We'll store it where the syscall number was saved (we don't need it anymore)
    # Stack layout at this point (offset from RSP):
    #   +0:  r15 (callee-saved)
    #   +8:  r14
    #   +16: r13
    #   +24: r12
    #   +32: rbp
    #   +40: rbx
    #   +48: RAX (syscall number) <- we'll overwrite this with return value
    #   +56: RDI (arg1)
    #   ...
    movq %rax, 48(%rsp)          # Save return value over saved syscall number

    # Disable interrupts for exit sequence
    cli

    # Restore callee-saved registers (CRITICAL: must restore user's RBX!)
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rbp
    popq %rbx                    # Restore user's RBX

    # Pop syscall frame
    popq %rax                    # This is now the return value (we saved it here)
    popq %rdi                    # Restore arg1
    popq %rsi                    # arg2
    popq %rdx                    # arg3
    popq %r10                    # arg4
    popq %r8                     # arg5
    popq %r9                     # arg6
    popq %rcx                    # return RIP
    popq %r11                    # saved RFLAGS
    popq %rsp                    # Restore user stack (user_rsp)

    # Return to userspace
    # SYSRETQ: RCX → RIP, R11 → RFLAGS, switch to Ring 3
    #
    # NOTE: SYSRET has strict requirements on segment selectors.
    # For now, we use IRETQ which is more flexible (but slower).
    # TODO: Optimize to use SYSRETQ once GDT is properly ordered.

    # Use IRETQ for safe return to Ring 3
    # Build IRET frame: SS, RSP, RFLAGS, CS, RIP

    # Push in reverse order (IRET pops: RIP, CS, RFLAGS, RSP, SS)
    pushq $0x23                  # SS (user data segment, ring 3)
    pushq %rsp                   # RSP (will be adjusted)
    addq $8, 0(%rsp)             # Adjust for the push we just did
    pushq %r11                   # RFLAGS (from R11)
    pushq $0x1B                  # CS (user code segment, ring 3)
    pushq %rcx                   # RIP (from RCX)

    iretq

.size syscall_entry, . - syscall_entry

# ============================================================================
# Jump to Userspace (Initial Entry)
# ============================================================================
# void jump_to_userspace(u64 entry_point, u64 user_stack)
#
# Used to start a new user process. Sets up IRET frame and jumps.
#
.global jump_to_userspace
.type jump_to_userspace, @function
jump_to_userspace:
    # Arguments:
    #   RDI = entry point (user RIP)
    #   RSI = user stack pointer

    # Disable interrupts during transition
    cli

    # Build IRET frame for Ring 3
    # Stack layout for IRETQ: RIP, CS, RFLAGS, RSP, SS

    pushq $0x23                  # SS (user data, ring 3)
    pushq %rsi                   # RSP (user stack)
    # Enable interrupts in userspace for true preemption
    # IF (bit 9) = 0x200, reserved bit 1 = 0x002
    pushq $0x202                 # RFLAGS (IF=1, reserved bit 1 = 1)
    pushq $0x1B                  # CS (user code, ring 3)
    pushq %rdi                   # RIP (entry point)

    # Clear all general purpose registers (security)
    xorq %rax, %rax
    xorq %rbx, %rbx
    xorq %rcx, %rcx
    xorq %rdx, %rdx
    xorq %rdi, %rdi
    xorq %rsi, %rsi
    xorq %rbp, %rbp
    xorq %r8, %r8
    xorq %r9, %r9
    xorq %r10, %r10
    xorq %r11, %r11
    xorq %r12, %r12
    xorq %r13, %r13
    xorq %r14, %r14
    xorq %r15, %r15

    # Jump to userspace!
    iretq

.size jump_to_userspace, . - jump_to_userspace

# ============================================================================
# Set Syscall Return Context
# ============================================================================
# void syscall_set_return_context(u64 rip, u64 rsp, u64 rflags)
#
# Used by sys_exit to restore parent context when a child process exits.
# Modifies the saved values on the syscall stack so that when syscall_entry
# returns, it goes to the specified context instead of the original caller.
#
.global syscall_set_return_context
.type syscall_set_return_context, @function
syscall_set_return_context:
    # Arguments:
    #   RDI = new user RIP
    #   RSI = new user RSP
    #   RDX = new user RFLAGS
    #
    # Update the global context variables - these will be used
    # by the next syscall return
    movq %rdi, syscall_user_rip(%rip)
    movq %rsi, syscall_user_rsp(%rip)
    movq %rdx, syscall_user_rflags(%rip)
    ret

.size syscall_set_return_context, . - syscall_set_return_context

# ============================================================================
# Jump to Userspace with Return Value
# ============================================================================
# void jump_to_userspace_with_retval(u64 entry_point, u64 user_stack, i64 retval)
#
# Similar to jump_to_userspace, but sets RAX to retval before jumping.
# Used by sys_exit to return to parent with the child's exit code.
#
.global jump_to_userspace_with_retval
.type jump_to_userspace_with_retval, @function
jump_to_userspace_with_retval:
    # Arguments:
    #   RDI = entry point (user RIP)
    #   RSI = user stack pointer
    #   RDX = return value (to put in RAX)

    # Disable interrupts during transition
    cli

    # Build IRET frame for Ring 3
    # Stack layout for IRETQ: RIP, CS, RFLAGS, RSP, SS

    pushq $0x23                  # SS (user data, ring 3)
    pushq %rsi                   # RSP (user stack)
    pushq $0x202                 # RFLAGS (IF=1, reserved bit 1 = 1)
    pushq $0x1B                  # CS (user code, ring 3)
    pushq %rdi                   # RIP (entry point)

    # Set return value in RAX (this is the key difference!)
    movq %rdx, %rax

    # Clear other registers (security)
    xorq %rbx, %rbx
    xorq %rcx, %rcx
    xorq %rdx, %rdx
    xorq %rdi, %rdi
    xorq %rsi, %rsi
    xorq %rbp, %rbp
    xorq %r8, %r8
    xorq %r9, %r9
    xorq %r10, %r10
    xorq %r11, %r11
    xorq %r12, %r12
    xorq %r13, %r13
    xorq %r14, %r14
    xorq %r15, %r15

    # Jump to userspace!
    iretq

.size jump_to_userspace_with_retval, . - jump_to_userspace_with_retval

# ============================================================================
# Userspace Syscall Stub (for testing - would be in user program)
# ============================================================================
# This is what userspace programs call to make syscalls.
# In a real system, this would be in a user library (libc equivalent).
#
# i64 harland_syscall(u64 num, u64 a1, u64 a2, u64 a3, u64 a4, u64 a5, u64 a6)
#
.global harland_syscall
.type harland_syscall, @function
harland_syscall:
    # Arguments already in the right registers:
    #   RDI = syscall number → move to RAX
    #   RSI = arg1 → move to RDI
    #   RDX = arg2 → move to RSI
    #   RCX = arg3 → move to RDX
    #   R8  = arg4 → move to R10
    #   R9  = arg5 → move to R8
    #   [stack] = arg6 → move to R9

    movq %rdi, %rax              # Syscall number
    movq %rsi, %rdi              # Arg 1
    movq %rdx, %rsi              # Arg 2
    movq %rcx, %rdx              # Arg 3
    movq %r8, %r10               # Arg 4 (R10, not RCX - SYSCALL clobbers RCX)
    movq %r9, %r8                # Arg 5
    movq 8(%rsp), %r9            # Arg 6 from stack

    syscall

    # Return value is in RAX
    ret

.size harland_syscall, . - harland_syscall
