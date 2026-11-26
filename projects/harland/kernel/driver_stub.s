# Boot-test stub for a kernel-spawned CPL-3 process (AGAST #4713,
# RING1_DRIVER.md section 2, Tests 1-3).
#
# postinit.ritz's driver-* boot tests copy the bytes between
# driver_stub_start and driver_stub_end into one user page of a child of
# pid 1 (syscall/runtime/process.ritz process_spawn_image) and enter it at
# CPL 3 through sched_prepare_user's ordinary frame (CS 0x23, SS 0x1B). The
# code is position-independent and uses no data outside the copied range.
# Only the boot-test mode spawns it.
#
# Entry: RDI = mode, RSI = arg1, both chosen by the kernel.
#   mode 0 (ENTER): report and exit.
#   mode 1 (FAULT): read address 0; the #PF kills the process (status 142).
#   mode 2 (SPIN):  busy-wait RSI TSC cycles at CPL 3 (the timer preempts
#                   it), then report and exit.
#   mode 3 (IRQ_WAIT, #4719): RSI is a CAP_TYPE_IRQ handle the kernel
#                   granted. Five DrvIrqWait calls, each checked; the exit
#                   status is the number of the first that failed, else 0:
#                   1  out_cap 0             -> Errno.Inval, out_count kept
#                   2  out_cap 9             -> Errno.Inval, out_count kept
#                   3  handle 0 (not held)   -> Errno.Perm, out_count kept
#                   4  out_cap 2, parks      -> 0: out_count 1, out[0] =
#                      { handle, EVENT_DATA }, out[1] kept
#                   5  the same again        -> 1 at the deadline:
#                      out_count 0, out[0] kept
#   mode 4 (CONSOLE_POLL, #4829): one poll(2) on { fd 0, POLLIN } with
#                   timeout RSI ms; the exit status is
#                   revents << 8 | (the return & 0xFF).
#   mode 5 (POLL_NVAL, #4829): poll(2) on { -1, POLLIN } and { 63, POLLIN }
#                   with no timeout; exit 0 if it returned 1 at once with
#                   revents 0 and POLLNVAL, else 1.
#   mode 6 (SHM_WAIT, #4727): RSI is the CAP_TYPE_IRQ handle; the kernel
#                   also granted SHM_H_FRAME (pid 1 holds the object too,
#                   and has posted DATA on it and latched the IRQ) and
#                   SHM_H_LONE (only the stub holds it). Nine checked calls;
#                   the exit status is the number of the first that failed:
#                   1  ShmNotify(frame, PEER_CLOSE)  -> Errno.Inval
#                   2  ShmNotify(frame, 0)           -> Errno.Inval
#                   3  ShmNotify(lone, DATA)         -> Errno.NoDev
#                   4  ShmNotify(handle 0, DATA)     -> Errno.Perm
#                   5  DrvIrqWait listing frame, out_cap 1 -> 0: out_count
#                      1, out[0] = { irq, DATA }, out[1] kept (the frame
#                      event stays latched)
#                   6  the same, out_cap 2 -> 2 at once: out_count 1,
#                      out[0] = { frame, DATA }, out[1] kept
#                   7  ShmNotify(frame, SPACE)       -> 0 (to pid 1's latch)
#                   8  ShmWait listing frame, deadline 0 -> 1: out_count 0,
#                      out[0] kept
#                   9  ShmWait, deadline SHM_WAIT_LONG_MS: parks until pid
#                      1 posts DATA -> 2: out_count 1, out[0] = { frame,
#                      DATA }
#   mode 7 (SERVICE, #4728): the ring-2 service stand-in, registered by
#                   the kernel; RSI = how many ATTACH records to collect.
#                   Each ShmWait lists no source (out_cap 8, deadline
#                   SHM_WAIT_LONG_MS) and must return 2; every record must
#                   be ATTACH, and the stub ShmMaps its handle: a VA counts
#                   as a map, Errno.Perm (the handle was dropped with a
#                   retired record) as a refused map, anything else fails.
#                   Exit status: records << 16 | refused << 8 | maps, or
#                   0xFF on a failure.
#   mode 8 (APP, #4728): NetAttach must return a handle, and a second
#                   NetAttach Errno.Exist; exit 0, else 1 or 2.
#   mode 9 (LINK, #4730): RSI is the link handle with CAP_RIGHT_PUBLISH
#                   (LINK_H_PLAIN is a second one without), or 0. Exit
#                   status: the number of the first failed step, else 0:
#                   1  NetInfo                 -> Errno.NoDev (RSI 0: done)
#                   2  NetPublish, link_seq 0  -> Errno.Again
#                   3  ShmMap(link)            -> a VA
#                   4  link_seq 1, NetPublish  -> Errno.Again
#                      (then NetInfo bytes LINK_MAC_WORD / LINK_MTU, fence,
#                      link_seq 2)
#                   5  NetPublish(LINK_H_PLAIN) -> Errno.Perm
#                   6  NetPublish(link)        -> 0
#                   7  NetInfo                 -> 0, the bytes it wrote
#                   8  NetInfo(kernel pointer) -> Errno.Fault
#                   9  link_seq 3, the MAC zeroed, NetPublish -> Errno.Again
#                      (the kernel then checks the snapshot kept generation
#                      2's bytes)
#   mode 21 (MMIO_MAP, #4720): RSI is a CAP_TYPE_MMIO handle on the
#                   boot-test window double. Exit status: the number of the
#                   first failed step, else 0:
#                   1  handle 0 (not held)   -> Errno.Perm
#                   2  the double            -> DRV_MMIO_BASE
#                   3  the byte at VA + MMIO_TEST_OFFSET is MMIO_TEST_BYTE
#                   4  the double again      -> DRV_MMIO_BASE + 4096
#                   (The guarded window's refusal is the boot test's
#                   scratch half: a second grant's generation is not
#                   known when the stub's argument is chosen.)
#   mode 22 (DMA_ALLOC, #4721): RSI is a CAP_TYPE_IRQ handle. Exit status:
#                   the number of the first failed step, else 0:
#                   1  handle 0 (not held)   -> Errno.Perm
#                   2  size 0                -> Errno.Inval
#                   3  size 4 MiB + 1        -> Errno.NoMem
#                   4  a kernel DmaAlloc     -> Errno.Fault
#                   5  size 8000             -> DRV_DMA_BASE, DmaAlloc
#                      { iova 0, size 8192 }
#                   6  all 8192 bytes read 0 (then are written)
#                   7  size 1                -> DRV_DMA_BASE + 8192
#   mode 23 (DMA_FREE, #4725): RSI is a CAP_TYPE_IRQ handle; the kernel has
#                   armed drv_dma_force_stuck(DRV_DMA_BASE + 20480), so the
#                   free of the run there is an unconfirmed invalidation.
#                   Exit status: the number of the first failed step, else 0:
#                   1  free, handle 0 (not held)       -> Errno.Perm
#                   2  alloc 8000                       -> DRV_DMA_BASE
#                   3  free BASE, 1 byte (one page)     -> Errno.Inval
#                   4  free BASE + 4096 (inside it)     -> Errno.Inval
#                   5  free BASE, 8000                  -> 0
#                   6  the same free again              -> Errno.Inval
#                   7  alloc 12288 -> BASE + 8192: too big for the freed
#                      range, and a fresh run starts past it, not over it
#                   8  alloc 4096                       -> BASE (reused)
#                   9  alloc 4096                       -> BASE + 4096
#                   10 alloc 4096                       -> BASE + 20480
#                   11 free BASE + 20480, 4096          -> 0 (quarantined)
#                   12 alloc 4096 -> BASE + 24576: the quarantined VA is
#                      not handed out again
# Report: Getpid, the CPL from CS, and arg1, packed into the exit status
#   (arg1 & 0x7FFF) << 16 | cpl << 8 | (pid & 0xFF)
# which the kernel decodes and logs as "[driver] pid N cpl C arg1 K".

.section .text

# Syscall numbers (kernel/src/syscall/numbers.ritz, enum Syscall)
.equ SYS_EXIT,   20
.equ SYS_GETPID, 23
.equ SYS_DRV_IRQ_WAIT, 220
.equ SYS_SHM_WAIT, 229
.equ SYS_SHM_NOTIFY, 230
.equ SYS_NET_INFO, 224
.equ SYS_NET_PUBLISH, 226
.equ SYS_SHM_MAP, 227
.equ SYS_NET_ATTACH, 228
.equ SYS_POLL,   7
.equ SYS_DRV_MMIO_MAP,  221
.equ SYS_DRV_DMA_ALLOC, 222
.equ SYS_DRV_DMA_FREE,  223

# Modes (postinit.ritz DRIVER_STUB_*)
.equ DRIVER_STUB_FAULT, 1
.equ DRIVER_STUB_SPIN,  2
.equ DRIVER_STUB_IRQ_WAIT, 3
.equ DRIVER_STUB_CONSOLE_POLL, 4
.equ DRIVER_STUB_POLL_NVAL, 5
.equ DRIVER_STUB_SHM_WAIT, 6
.equ DRIVER_STUB_SERVICE, 7
.equ DRIVER_STUB_APP, 8
.equ DRIVER_STUB_LINK, 9
.equ DRIVER_STUB_MMIO_MAP, 21
.equ DRIVER_STUB_DMA_ALLOC, 22
.equ DRIVER_STUB_DMA_FREE, 23

# DrvMmioMap and DrvDmaAlloc (mm/vmm.ritz, driver_abi/src/dma.ritz,
# postinit.ritz MMIO_TEST_*)
.equ DRV_MMIO_BASE,   0x7E8000000000
.equ DRV_DMA_BASE,    0x7E0000000000
.equ MMIO_TEST_OFFSET, 0x123
.equ MMIO_TEST_BYTE,  0xA5
.equ DA_IOVA,         0
.equ DA_SIZE,         8
.equ DMA_TEST_SIZE,   8000
.equ DMA_TEST_PAGES_BYTES, 8192
.equ DMA_OVER_MAX,    0x400001
.equ KERNEL_ADDR,     0xFFFF800000000000
.equ ERRNO_NOMEM,     -12
.equ ERRNO_FAULT,     -14

# ritzlib.sys PollFd (8 bytes): fd i32, events i16, revents i16
.equ PFD_FD,      0
.equ PFD_EVENTS,  4
.equ PFD_REVENTS, 6
.equ PFD_SIZE,    8
.equ POLLIN,      1
.equ POLLNVAL,    32
.equ POLL_NOT_OPEN, 63

# driver_abi/src/wait.ritz: WaitRequest (40 bytes) and WaitEvent (16)
.equ WR_SOURCES,      0
.equ WR_SOURCE_COUNT, 8
.equ WR_OUT_CAP,      12
.equ WR_OUT,          16
.equ WR_DEADLINE,     24
.equ WR_OUT_COUNT,    32
.equ WR_PAD,          36
.equ WR_EVENTS,       48          # two WaitEvents after the request
.equ WE_HANDLE,       0
.equ WE_BITS,         8
.equ WE_SIZE,         16
.equ EVENT_DATA,      1
.equ ERRNO_PERM,      -1
.equ ERRNO_INVAL,     -22
.equ KEPT_COUNT,      0x5A        # out_count before a call that must not write it
# Mode 6 (postinit.ritz SHM_TEST_*): a WaitSource after the two out slots,
# the stub's handles (index | generation << 32, a fresh table's second and
# third grants) and the event bits it sends.
.equ WR_SOURCE,       80          # one WaitSource { handle, mask, _pad }
.equ WS_HANDLE,       0
.equ WS_MASK,         8
.equ WS_PAD,          12
.equ SHM_H_FRAME,     0x200000001
.equ SHM_H_LONE,      0x300000002
.equ EVENT_SPACE,     2
.equ EVENT_PEER_CLOSE, 4
.equ ERRNO_NODEV,     -19
.equ SHM_WAIT_LONG_MS, 5000
# Modes 7-9 (postinit.ritz ATTACH_* and LINK_TEST_*; driver_abi/src/link.ritz)
.equ EVENT_ATTACH,    64
.equ ERRNO_AGAIN,     -11
.equ ERRNO_EXIST,     -17
.equ SERVICE_OUT_CAP, 8
.equ SERVICE_END,     176         # where the service keeps its records' end
.equ LINK_SEQ_OFF,    0x20
.equ LINK_H_PLAIN,    0x200000001
.equ LINK_MAC_WORD,   0x0101013047005452   # 52:54:00:47:30:01, link_up 1, type 1
.equ LINK_MTU,        1500

.global driver_stub_start
.type driver_stub_start, @function
driver_stub_start:
    # syscall_entry.s restores the callee-saved registers, so r12-r14 hold
    # the entry arguments across Getpid.
    movq %rdi, %r12
    movq %rsi, %r13
    cmpq $DRIVER_STUB_FAULT, %r12
    jne .Ldriver_stub_not_fault
    xorl %eax, %eax
    movq (%rax), %rax            # #PF at CPL 3: never returns
    ud2
.Ldriver_stub_not_fault:
    cmpq $DRIVER_STUB_IRQ_WAIT, %r12
    je .Ldriver_stub_irq_wait
    cmpq $DRIVER_STUB_MMIO_MAP, %r12
    je .Ldriver_stub_mmio_map
    cmpq $DRIVER_STUB_DMA_ALLOC, %r12
    je .Ldriver_stub_dma_alloc
    cmpq $DRIVER_STUB_DMA_FREE, %r12
    je .Ldriver_stub_dma_free
    cmpq $DRIVER_STUB_CONSOLE_POLL, %r12
    je .Ldriver_stub_console_poll
    cmpq $DRIVER_STUB_POLL_NVAL, %r12
    je .Ldriver_stub_poll_nval
    cmpq $DRIVER_STUB_SHM_WAIT, %r12
    je .Ldriver_stub_shm_wait
    cmpq $DRIVER_STUB_SERVICE, %r12
    je .Ldriver_stub_service
    cmpq $DRIVER_STUB_APP, %r12
    je .Ldriver_stub_app
    cmpq $DRIVER_STUB_LINK, %r12
    je .Ldriver_stub_link
    cmpq $DRIVER_STUB_SPIN, %r12
    jne .Ldriver_stub_report
    rdtsc
    shlq $32, %rdx
    orq %rdx, %rax
    leaq (%rax,%r13), %r14       # the deadline: now + arg1 cycles
.Ldriver_stub_spin:
    pause
    rdtsc
    shlq $32, %rdx
    orq %rdx, %rax
    cmpq %r14, %rax
    jb .Ldriver_stub_spin
.Ldriver_stub_report:
    movq $SYS_GETPID, %rax
    syscall
    movzbl %al, %edi             # pid & 0xFF
    movl %cs, %eax
    andl $3, %eax                # the CPL this code runs at
    shll $8, %eax
    orl %eax, %edi
    movl %r13d, %eax
    andl $0x7FFF, %eax
    shll $16, %eax
    orl %eax, %edi
    movq $SYS_EXIT, %rax
    syscall
    ud2                          # exit does not return

# Mode 3. r14 = the request and its two out slots, on the user stack; r15 =
# the step number reported if a check fails.
.Ldriver_stub_irq_wait:
    subq $80, %rsp
    movq %rsp, %r14
    movabsq $0xEEEEEEEEEEEEEEEE, %rbx   # the untouched out-slot pattern

    movl $1, %r15d                       # 1: out_cap 0
    xorl %esi, %esi
    call .Lirq_wait_call_cap
    cmpq $ERRNO_INVAL, %rax
    jne .Lirq_wait_fail
    cmpl $KEPT_COUNT, WR_OUT_COUNT(%r14)
    jne .Lirq_wait_fail

    movl $2, %r15d                       # 2: out_cap 9
    movl $9, %esi
    call .Lirq_wait_call_cap
    cmpq $ERRNO_INVAL, %rax
    jne .Lirq_wait_fail
    cmpl $KEPT_COUNT, WR_OUT_COUNT(%r14)
    jne .Lirq_wait_fail

    movl $3, %r15d                       # 3: a handle it does not hold
    movl $2, %esi
    call .Lirq_wait_fill
    movq $SYS_DRV_IRQ_WAIT, %rax
    xorl %edi, %edi
    movq %r14, %rsi
    syscall
    cmpq $ERRNO_PERM, %rax
    jne .Lirq_wait_fail
    cmpl $KEPT_COUNT, WR_OUT_COUNT(%r14)
    jne .Lirq_wait_fail

    movl $4, %r15d                       # 4: parks until its IRQ is latched
    movl $2, %esi
    call .Lirq_wait_call_cap
    cmpq $0, %rax
    jne .Lirq_wait_fail
    cmpl $1, WR_OUT_COUNT(%r14)
    jne .Lirq_wait_fail
    cmpq %r13, WR_EVENTS+WE_HANDLE(%r14)
    jne .Lirq_wait_fail
    cmpl $EVENT_DATA, WR_EVENTS+WE_BITS(%r14)
    jne .Lirq_wait_fail
    cmpq %rbx, WR_EVENTS+WE_SIZE+WE_HANDLE(%r14)
    jne .Lirq_wait_fail

    movl $5, %r15d                       # 5: seen = latched: the deadline
    movl $2, %esi
    call .Lirq_wait_call_cap
    cmpq $1, %rax
    jne .Lirq_wait_fail
    cmpl $0, WR_OUT_COUNT(%r14)
    jne .Lirq_wait_fail
    cmpq %rbx, WR_EVENTS+WE_HANDLE(%r14)
    jne .Lirq_wait_fail

    xorl %r15d, %r15d                    # every check held
.Lirq_wait_fail:
    movl %r15d, %edi
    movq $SYS_EXIT, %rax
    syscall
    ud2

# Fill the request for out_cap ESI (no sources, out = the two slots,
# out_count KEPT_COUNT, both slots the untouched pattern) and call
# DrvIrqWait with the granted handle (r13). RAX = the result.
.Lirq_wait_call_cap:
    call .Lirq_wait_fill
    movq $SYS_DRV_IRQ_WAIT, %rax
    movq %r13, %rdi
    movq %r14, %rsi
    syscall
    ret

.Lirq_wait_fill:
    movq $0, WR_SOURCES(%r14)
    movl $0, WR_SOURCE_COUNT(%r14)
    movl %esi, WR_OUT_CAP(%r14)
    leaq WR_EVENTS(%r14), %rax
    movq %rax, WR_OUT(%r14)
    movq $0, WR_DEADLINE(%r14)
    movl $KEPT_COUNT, WR_OUT_COUNT(%r14)
    movl $0, WR_PAD(%r14)
    movq %rbx, WR_EVENTS+WE_HANDLE(%r14)
    movq %rbx, WR_EVENTS+WE_BITS(%r14)
    movq %rbx, WR_EVENTS+WE_SIZE+WE_HANDLE(%r14)
    movq %rbx, WR_EVENTS+WE_SIZE+WE_BITS(%r14)
    ret

# Mode 4: poll { 0, POLLIN } for r13 ms.
.Ldriver_stub_console_poll:
    subq $16, %rsp
    movl $0, PFD_FD(%rsp)
    movw $POLLIN, PFD_EVENTS(%rsp)
    movw $0x7777, PFD_REVENTS(%rsp)     # the kernel must write it
    movq $SYS_POLL, %rax
    movq %rsp, %rdi
    movl $1, %esi
    movq %r13, %rdx
    syscall
    movzbl %al, %edi
    movzwl PFD_REVENTS(%rsp), %eax
    shll $8, %eax
    orl %eax, %edi
    movq $SYS_EXIT, %rax
    syscall
    ud2

# Mode 5: a skipped entry and a number that names no file, no timeout.
.Ldriver_stub_poll_nval:
    subq $16, %rsp
    movl $-1, PFD_FD(%rsp)
    movw $POLLIN, PFD_EVENTS(%rsp)
    movw $0x7777, PFD_REVENTS(%rsp)
    movl $POLL_NOT_OPEN, PFD_SIZE+PFD_FD(%rsp)
    movw $POLLIN, PFD_SIZE+PFD_EVENTS(%rsp)
    movw $0x7777, PFD_SIZE+PFD_REVENTS(%rsp)
    movq $SYS_POLL, %rax
    movq %rsp, %rdi
    movl $2, %esi
    movq $-1, %rdx
    syscall
    movl $1, %edi
    cmpq $1, %rax
    jne .Lpoll_nval_exit
    cmpw $0, PFD_REVENTS(%rsp)
    jne .Lpoll_nval_exit
    cmpw $POLLNVAL, PFD_SIZE+PFD_REVENTS(%rsp)
    jne .Lpoll_nval_exit
    xorl %edi, %edi
.Lpoll_nval_exit:
    movq $SYS_EXIT, %rax
    syscall
    ud2

# Mode 21. r15 = the step reported if a check fails.
.Ldriver_stub_mmio_map:
    movl $1, %r15d                       # 1: a handle it does not hold
    movq $SYS_DRV_MMIO_MAP, %rax
    xorl %edi, %edi
    syscall
    cmpq $ERRNO_PERM, %rax
    jne .Lmmio_fail
    movl $2, %r15d                       # 2: the double, at the window base
    movq $SYS_DRV_MMIO_MAP, %rax
    movq %r13, %rdi
    syscall
    movabsq $DRV_MMIO_BASE, %rcx
    cmpq %rcx, %rax
    jne .Lmmio_fail
    movl $3, %r15d                       # 3: its byte, read uncached
    cmpb $MMIO_TEST_BYTE, MMIO_TEST_OFFSET(%rax)
    jne .Lmmio_fail
    movl $4, %r15d                       # 4: a second map, the next page
    movq $SYS_DRV_MMIO_MAP, %rax
    movq %r13, %rdi
    syscall
    movabsq $DRV_MMIO_BASE+4096, %rcx
    cmpq %rcx, %rax
    jne .Lmmio_fail
    xorl %r15d, %r15d
.Lmmio_fail:
    movl %r15d, %edi
    movq $SYS_EXIT, %rax
    syscall
    ud2

# Mode 22. r14 = the DmaAlloc, on the user stack; r15 = the failing step.
.Ldriver_stub_dma_alloc:
    subq $16, %rsp
    movq %rsp, %r14
    movl $1, %r15d                       # 1: a handle it does not hold
    xorl %edi, %edi
    movl $4096, %esi
    movq %r14, %rdx
    call .Ldma_call
    cmpq $ERRNO_PERM, %rax
    jne .Ldma_fail
    movl $2, %r15d                       # 2: size 0
    movq %r13, %rdi
    xorl %esi, %esi
    movq %r14, %rdx
    call .Ldma_call
    cmpq $ERRNO_INVAL, %rax
    jne .Ldma_fail
    movl $3, %r15d                       # 3: above DMA_ALLOC_MAX
    movq %r13, %rdi
    movl $DMA_OVER_MAX, %esi
    movq %r14, %rdx
    call .Ldma_call
    cmpq $ERRNO_NOMEM, %rax
    jne .Ldma_fail
    movl $4, %r15d                       # 4: a DmaAlloc it can't write
    movq %r13, %rdi
    movl $4096, %esi
    movabsq $KERNEL_ADDR, %rdx
    call .Ldma_call
    cmpq $ERRNO_FAULT, %rax
    jne .Ldma_fail
    movl $5, %r15d                       # 5: two pages at the window base
    movq %r13, %rdi
    movl $DMA_TEST_SIZE, %esi
    movq %r14, %rdx
    call .Ldma_call
    movabsq $DRV_DMA_BASE, %rcx
    cmpq %rcx, %rax
    jne .Ldma_fail
    cmpq $0, DA_IOVA(%r14)
    jne .Ldma_fail
    cmpq $DMA_TEST_PAGES_BYTES, DA_SIZE(%r14)
    jne .Ldma_fail
    movl $6, %r15d                       # 6: zeroed, and writable
    xorl %ecx, %ecx
.Ldma_zeroed:
    cmpq $0, (%rax,%rcx,8)
    jne .Ldma_fail
    notq (%rax,%rcx,8)
    incq %rcx
    cmpq $DMA_TEST_PAGES_BYTES/8, %rcx
    jb .Ldma_zeroed
    movl $7, %r15d                       # 7: the next run follows it
    movq %r13, %rdi
    movl $1, %esi
    movq %r14, %rdx
    call .Ldma_call
    movabsq $DRV_DMA_BASE+DMA_TEST_PAGES_BYTES, %rcx
    cmpq %rcx, %rax
    jne .Ldma_fail
    xorl %r15d, %r15d
.Ldma_fail:
    movl %r15d, %edi
    movq $SYS_EXIT, %rax
    syscall
    ud2

# Mode 6. r14 = the request, its two out slots and one source, on the user
# stack; r15 = the step number reported if a check fails; r13 = the IRQ
# handle.
.Ldriver_stub_shm_wait:
    subq $96, %rsp
    movq %rsp, %r14
    movabsq $0xEEEEEEEEEEEEEEEE, %rbx   # the untouched out-slot pattern

    movl $1, %r15d                       # 1: a userspace PEER_CLOSE
    movabsq $SHM_H_FRAME, %rdi
    movl $EVENT_PEER_CLOSE, %esi
    call .Lshm_notify
    cmpq $ERRNO_INVAL, %rax
    jne .Lshm_wait_fail

    movl $2, %r15d                       # 2: no bits
    movabsq $SHM_H_FRAME, %rdi
    xorl %esi, %esi
    call .Lshm_notify
    cmpq $ERRNO_INVAL, %rax
    jne .Lshm_wait_fail

    movl $3, %r15d                       # 3: no other holder
    movabsq $SHM_H_LONE, %rdi
    movl $EVENT_DATA, %esi
    call .Lshm_notify
    cmpq $ERRNO_NODEV, %rax
    jne .Lshm_wait_fail

    movl $4, %r15d                       # 4: a handle it does not hold
    xorl %edi, %edi
    movl $EVENT_DATA, %esi
    call .Lshm_notify
    cmpq $ERRNO_PERM, %rax
    jne .Lshm_wait_fail

    movl $5, %r15d                       # 5: IRQ and frame hot, room for one
    movl $1, %esi
    xorl %edx, %edx
    call .Lshm_fill
    call .Lshm_irq_wait
    cmpq $0, %rax
    jne .Lshm_wait_fail
    cmpl $1, WR_OUT_COUNT(%r14)
    jne .Lshm_wait_fail
    cmpq %r13, WR_EVENTS+WE_HANDLE(%r14)
    jne .Lshm_wait_fail
    cmpl $EVENT_DATA, WR_EVENTS+WE_BITS(%r14)
    jne .Lshm_wait_fail
    cmpq %rbx, WR_EVENTS+WE_SIZE+WE_HANDLE(%r14)
    jne .Lshm_wait_fail

    movl $6, %r15d                       # 6: the frame event it left latched
    movl $2, %esi
    xorl %edx, %edx
    call .Lshm_fill
    call .Lshm_irq_wait
    cmpq $2, %rax
    jne .Lshm_wait_fail
    call .Lshm_frame_record
    jne .Lshm_wait_fail

    movl $7, %r15d                       # 7: SPACE to pid 1
    movabsq $SHM_H_FRAME, %rdi
    movl $EVENT_SPACE, %esi
    call .Lshm_notify
    cmpq $0, %rax
    jne .Lshm_wait_fail

    movl $8, %r15d                       # 8: nothing hot, deadline 0
    movl $2, %esi
    xorl %edx, %edx
    call .Lshm_fill
    call .Lshm_wait_call
    cmpq $1, %rax
    jne .Lshm_wait_fail
    cmpl $0, WR_OUT_COUNT(%r14)
    jne .Lshm_wait_fail
    cmpq %rbx, WR_EVENTS+WE_HANDLE(%r14)
    jne .Lshm_wait_fail

    movl $9, %r15d                       # 9: parks until pid 1 posts DATA
    movl $2, %esi
    movl $SHM_WAIT_LONG_MS, %edx
    call .Lshm_fill
    call .Lshm_wait_call
    cmpq $2, %rax
    jne .Lshm_wait_fail
    call .Lshm_frame_record
    jne .Lshm_wait_fail

    xorl %r15d, %r15d                    # every check held
.Lshm_wait_fail:
    movl %r15d, %edi
    movq $SYS_EXIT, %rax
    syscall
    ud2

# DrvDmaAlloc(RDI, RSI, RDX): r10 is not an argument here. RAX = the result.
.Ldma_call:
    movq $SYS_DRV_DMA_ALLOC, %rax
    syscall
    ret

# Mode 23. r14 = the DmaAlloc, on the user stack; r15 = the failing step;
# rbx = DRV_DMA_BASE.
.Ldriver_stub_dma_free:
    subq $16, %rsp
    movq %rsp, %r14
    movabsq $DRV_DMA_BASE, %rbx
    movl $1, %r15d                       # 1: a handle it does not hold
    xorl %edi, %edi
    movq %rbx, %rsi
    movl $4096, %edx
    call .Ldma_free_call
    cmpq $ERRNO_PERM, %rax
    jne .Lfree_fail
    movl $2, %r15d                       # 2: two pages at the window base
    movl $DMA_TEST_SIZE, %esi
    call .Lfree_alloc
    cmpq %rbx, %rax
    jne .Lfree_fail
    movl $3, %r15d                       # 3: the right VA, one page short
    movq %rbx, %rsi
    movl $1, %edx
    call .Lfree_mine
    cmpq $ERRNO_INVAL, %rax
    jne .Lfree_fail
    movl $4, %r15d                       # 4: inside the run, not its start
    leaq 4096(%rbx), %rsi
    movl $4096, %edx
    call .Lfree_mine
    cmpq $ERRNO_INVAL, %rax
    jne .Lfree_fail
    movl $5, %r15d                       # 5: the run, its size unrounded
    movq %rbx, %rsi
    movl $DMA_TEST_SIZE, %edx
    call .Lfree_mine
    testq %rax, %rax
    jne .Lfree_fail
    movl $6, %r15d                       # 6: it is gone
    movq %rbx, %rsi
    movl $DMA_TEST_SIZE, %edx
    call .Lfree_mine
    cmpq $ERRNO_INVAL, %rax
    jne .Lfree_fail
    movl $7, %r15d                       # 7: bigger than it: past it, fresh
    movl $12288, %esi
    call .Lfree_alloc
    leaq 8192(%rbx), %rcx
    cmpq %rcx, %rax
    jne .Lfree_fail
    movl $8, %r15d                       # 8: the freed range, front first
    movl $4096, %esi
    call .Lfree_alloc
    cmpq %rbx, %rax
    jne .Lfree_fail
    movl $9, %r15d                       # 9: then the rest of it
    movl $4096, %esi
    call .Lfree_alloc
    leaq 4096(%rbx), %rcx
    cmpq %rcx, %rax
    jne .Lfree_fail
    movl $10, %r15d                      # 10: then a fresh page
    movl $4096, %esi
    call .Lfree_alloc
    leaq 20480(%rbx), %rcx
    cmpq %rcx, %rax
    jne .Lfree_fail
    movl $11, %r15d                      # 11: its free is quarantined: still 0
    leaq 20480(%rbx), %rsi
    movl $4096, %edx
    call .Lfree_mine
    testq %rax, %rax
    jne .Lfree_fail
    movl $12, %r15d                      # 12: that VA is not handed out again
    movl $4096, %esi
    call .Lfree_alloc
    leaq 24576(%rbx), %rcx
    cmpq %rcx, %rax
    jne .Lfree_fail
    xorl %r15d, %r15d
.Lfree_fail:
    movl %r15d, %edi
    movq $SYS_EXIT, %rax
    syscall
    ud2

# DrvDmaAlloc(r13, RSI, r14). RAX = the result.
.Lfree_alloc:
    movq %r13, %rdi
    movq %r14, %rdx
    jmp .Ldma_call

# DrvDmaFree(r13, RSI, RDX). RAX = the result.
.Lfree_mine:
    movq %r13, %rdi
# DrvDmaFree(RDI, RSI, RDX). RAX = the result.
.Ldma_free_call:
    movq $SYS_DRV_DMA_FREE, %rax
    syscall
    ret

# ShmNotify(RDI, RSI). RAX = the result.
.Lshm_notify:
    movq $SYS_SHM_NOTIFY, %rax
    syscall
    ret

.Lshm_irq_wait:
    movq $SYS_DRV_IRQ_WAIT, %rax
    movq %r13, %rdi
    movq %r14, %rsi
    syscall
    ret

.Lshm_wait_call:
    movq $SYS_SHM_WAIT, %rax
    movq %r14, %rdi
    syscall
    ret

# ZF set if the call stored one record, { frame, DATA }, and kept out[1].
.Lshm_frame_record:
    cmpl $1, WR_OUT_COUNT(%r14)
    jne 1f
    movabsq $SHM_H_FRAME, %rax
    cmpq %rax, WR_EVENTS+WE_HANDLE(%r14)
    jne 1f
    cmpl $EVENT_DATA, WR_EVENTS+WE_BITS(%r14)
    jne 1f
    cmpq %rbx, WR_EVENTS+WE_SIZE+WE_HANDLE(%r14)
1:
    ret

# Fill the request for out_cap ESI and deadline RDX ms: one source, the
# frame handle for DATA; out = the two slots, both the untouched pattern;
# out_count KEPT_COUNT.
.Lshm_fill:
    leaq WR_SOURCE(%r14), %rax
    movq %rax, WR_SOURCES(%r14)
    movl $1, WR_SOURCE_COUNT(%r14)
    movl %esi, WR_OUT_CAP(%r14)
    leaq WR_EVENTS(%r14), %rax
    movq %rax, WR_OUT(%r14)
    movq %rdx, WR_DEADLINE(%r14)
    movl $KEPT_COUNT, WR_OUT_COUNT(%r14)
    movl $0, WR_PAD(%r14)
    movq %rbx, WR_EVENTS+WE_HANDLE(%r14)
    movq %rbx, WR_EVENTS+WE_BITS(%r14)
    movq %rbx, WR_EVENTS+WE_SIZE+WE_HANDLE(%r14)
    movq %rbx, WR_EVENTS+WE_SIZE+WE_BITS(%r14)
    movabsq $SHM_H_FRAME, %rax
    movq %rax, WR_SOURCE+WS_HANDLE(%r14)
    movl $EVENT_DATA, WR_SOURCE+WS_MASK(%r14)
    movl $0, WR_SOURCE+WS_PAD(%r14)
    ret

# Mode 7. r14 = the request and eight out slots; r15 = records so far; rbx
# = refused << 8 | maps; r12 walks the records one return copied.
.Ldriver_stub_service:
    subq $192, %rsp
    movq %rsp, %r14
    xorl %r15d, %r15d
    xorl %ebx, %ebx
.Lservice_wait:
    movq $0, WR_SOURCES(%r14)
    movl $0, WR_SOURCE_COUNT(%r14)
    movl $SERVICE_OUT_CAP, WR_OUT_CAP(%r14)
    leaq WR_EVENTS(%r14), %rax
    movq %rax, WR_OUT(%r14)
    movq $SHM_WAIT_LONG_MS, WR_DEADLINE(%r14)
    movl $0, WR_OUT_COUNT(%r14)
    movl $0, WR_PAD(%r14)
    movq $SYS_SHM_WAIT, %rax
    movq %r14, %rdi
    syscall
    cmpq $2, %rax
    jne .Lservice_fail
    movl WR_OUT_COUNT(%r14), %eax
    testl %eax, %eax
    jz .Lservice_fail
    shlq $4, %rax                        # * WE_SIZE
    leaq WR_EVENTS(%r14,%rax), %rax
    movq %rax, SERVICE_END(%r14)
    leaq WR_EVENTS(%r14), %r12
.Lservice_record:
    cmpl $EVENT_ATTACH, WE_BITS(%r12)
    jne .Lservice_fail
    movq $SYS_SHM_MAP, %rax
    movq WE_HANDLE(%r12), %rdi
    syscall
    cmpq $ERRNO_PERM, %rax
    je .Lservice_refused
    testq %rax, %rax
    jle .Lservice_fail
    incq %rbx                            # mapped
    jmp .Lservice_next
.Lservice_refused:
    addq $0x100, %rbx                    # dropped with its retired record
.Lservice_next:
    incq %r15
    addq $WE_SIZE, %r12
    cmpq SERVICE_END(%r14), %r12
    jb .Lservice_record
    cmpq %r13, %r15
    jb .Lservice_wait
    movq %r15, %rdi
    shlq $16, %rdi
    orq %rbx, %rdi
    movq $SYS_EXIT, %rax
    syscall
    ud2
.Lservice_fail:
    movl $0xFF, %edi
    movq $SYS_EXIT, %rax
    syscall
    ud2

# Mode 8: attach, then attach again while holding the handle.
.Ldriver_stub_app:
    movq $SYS_NET_ATTACH, %rax
    syscall
    movl $1, %edi
    testq %rax, %rax
    js .Lapp_exit
    movq $SYS_NET_ATTACH, %rax
    syscall
    movl $2, %edi
    cmpq $ERRNO_EXIST, %rax
    jne .Lapp_exit
    xorl %edi, %edi
.Lapp_exit:
    movq $SYS_EXIT, %rax
    syscall
    ud2

# Mode 9. r14 = a NetInfo buffer; r12 = the mapped link page; r15 = the
# step number reported if a check fails.
.Ldriver_stub_link:
    subq $32, %rsp
    movq %rsp, %r14
    movl $1, %r15d                       # 1: nothing published
    movq $SYS_NET_INFO, %rax
    movq %r14, %rdi
    syscall
    cmpq $ERRNO_NODEV, %rax
    jne .Llink_fail
    testq %r13, %r13
    jz .Llink_done
    movl $2, %r15d                       # 2: link_seq 0 is unpublished
    call .Llink_publish
    cmpq $ERRNO_AGAIN, %rax
    jne .Llink_fail
    movl $3, %r15d                       # 3: map the link page
    movq $SYS_SHM_MAP, %rax
    movq %r13, %rdi
    syscall
    testq %rax, %rax
    jle .Llink_fail
    movq %rax, %r12
    movl $4, %r15d                       # 4: link_seq 1, a write in progress
    movq $1, LINK_SEQ_OFF(%r12)
    mfence
    call .Llink_publish
    cmpq $ERRNO_AGAIN, %rax
    jne .Llink_fail
    movabsq $LINK_MAC_WORD, %rax
    movq %rax, 0(%r12)
    movl $LINK_MTU, 8(%r12)
    mfence
    movq $2, LINK_SEQ_OFF(%r12)          # generation 2
    movl $5, %r15d                       # 5: no CAP_RIGHT_PUBLISH
    movq $SYS_NET_PUBLISH, %rax
    movabsq $LINK_H_PLAIN, %rdi
    syscall
    cmpq $ERRNO_PERM, %rax
    jne .Llink_fail
    movl $6, %r15d                       # 6: the publish
    call .Llink_publish
    testq %rax, %rax
    jne .Llink_fail
    movl $7, %r15d                       # 7: NetInfo copies the snapshot
    movq $0, 0(%r14)
    movq $0, 8(%r14)
    movq $SYS_NET_INFO, %rax
    movq %r14, %rdi
    syscall
    testq %rax, %rax
    jne .Llink_fail
    movabsq $LINK_MAC_WORD, %rax
    cmpq %rax, 0(%r14)
    jne .Llink_fail
    cmpl $LINK_MTU, 8(%r14)
    jne .Llink_fail
    movl $8, %r15d                       # 8: not the caller's memory
    movq $SYS_NET_INFO, %rax
    movabsq $KERNEL_ADDR, %rdi
    syscall
    cmpq $ERRNO_FAULT, %rax
    jne .Llink_fail
    movl $9, %r15d                       # 9: link_seq 3 over scribbled bytes
    movq $3, LINK_SEQ_OFF(%r12)
    mfence
    movq $0, 0(%r12)
    call .Llink_publish
    cmpq $ERRNO_AGAIN, %rax
    jne .Llink_fail
.Llink_done:
    xorl %r15d, %r15d
.Llink_fail:
    movl %r15d, %edi
    movq $SYS_EXIT, %rax
    syscall
    ud2

# NetPublish with the publish handle (r13). RAX = the result.
.Llink_publish:
    movq $SYS_NET_PUBLISH, %rax
    movq %r13, %rdi
    syscall
    ret

.size driver_stub_start, . - driver_stub_start

.global driver_stub_end
driver_stub_end:
