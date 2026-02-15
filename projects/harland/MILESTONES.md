# Harland Milestones

> From "Hello World" to a portable Ritz runtime

## Overview

This document defines concrete milestones for Harland development. Each milestone builds on the previous and has clear success criteria that can be tested.

The ultimate goal: **Ritz runs natively on Harland, Linux, Windows, macOS, and ARM**—with a unified syscall abstraction layer.

---

## Milestone 0: Build Infrastructure
**Goal**: Ritz compiles to x86-64 freestanding binary

### Deliverables
- [ ] `ritzc --target x86_64-none-elf` works
- [ ] LLVM IR → object file → ELF linking works
- [ ] Makefile builds kernel.elf from .ritz sources
- [ ] Unit tests run on host (Linux x86-64)

### Success Criteria
```bash
$ make kernel.elf
$ file kernel.elf
kernel.elf: ELF 64-bit LSB executable, x86-64, statically linked
```

---

## Milestone 1: Hello World on Serial Console
**Goal**: Kernel boots in QEMU and prints to serial port

### Deliverables
- [ ] UEFI bootloader (stage1.ritz) loads kernel
- [ ] Kernel initializes serial port (COM1: 0x3F8)
- [ ] Kernel prints "Hello from Harland!" to serial
- [ ] QEMU `-serial mon:stdio` shows output
- [ ] Automated test validates output

### Success Criteria
```bash
$ make run | head -5
Harland Stage 1 Bootloader
Loading kernel...
Jumping to kernel...

Hello from Harland!
```

### Key Code
```ritz
# kernel/main.ritz
kernel_main(boot_info: ptr[BootInfo]):
    serial_init()
    serial_print("Hello from Harland!\n")
    halt()
```

---

## Milestone 2: Framebuffer Console
**Goal**: Text output to graphical framebuffer

### Deliverables
- [ ] Parse GOP framebuffer info from UEFI
- [ ] Implement basic font rendering (8x16 bitmap font)
- [ ] Console abstraction: `Console` trait with `write_char`, `write_str`
- [ ] Serial and framebuffer consoles both work
- [ ] Scrolling works

### Success Criteria
- QEMU window shows text output
- Text wraps and scrolls correctly
- Both serial and framebuffer show same output

### Key Code
```ritz
# kernel/console/mod.ritz
@trait
Console:
    write_char(c: u8)
    write_str(s: ptr[u8])
    clear()

# kernel/console/framebuffer.ritz
@class
FramebufferConsole:
    fb: ptr[u32]
    width: u32
    height: u32
    pitch: u32
    cursor_x: u32
    cursor_y: u32

    @impl Console
    write_char(c: u8):
        if c == '\n':
            cursor_x = 0
            cursor_y += 16
            if cursor_y >= height:
                scroll_up()
        else:
            draw_glyph(cursor_x, cursor_y, c)
            cursor_x += 8
```

---

## Milestone 3: CPU Initialization & GDT/IDT
**Goal**: Proper CPU setup with interrupt handling

### Deliverables
- [ ] GDT with kernel/user code/data segments
- [ ] IDT with all 256 entries
- [ ] Exception handlers (divide by zero, page fault, etc.)
- [ ] ISR stubs that save/restore state and call Ritz handlers
- [ ] Panic handler that prints register dump

### Success Criteria
```ritz
@test @integration
test_divide_by_zero():
    install_handler(EXCEPTION_DIVIDE, test_handler)

    x = 1 / 0  # Triggers exception

    assert handler_called == true
    assert exception_type == EXCEPTION_DIVIDE
```

### Key Code
```ritz
# kernel/arch/x86_64/idt.ritz
@packed @class
IDTEntry:
    offset_low: u16
    selector: u16
    ist: u8
    type_attr: u8
    offset_mid: u16
    offset_high: u32
    zero: u32

    set_handler(handler: u64, selector: u16, ist: u8, type_attr: u8):
        offset_low = (handler & 0xFFFF) as u16
        offset_mid = ((handler >> 16) & 0xFFFF) as u16
        offset_high = ((handler >> 32) & 0xFFFFFFFF) as u32
        self.selector = selector
        self.ist = ist
        self.type_attr = type_attr
        zero = 0
```

---

## Milestone 4: Page Tables & Virtual Memory
**Goal**: 4-level paging with higher-half kernel

### Deliverables
- [ ] Physical frame allocator (bitmap-based)
- [ ] Page table structure (`PageTable`, `PageTableEntry`)
- [ ] `map_page(virtual, physical, flags)`
- [ ] `unmap_page(virtual)`
- [ ] Higher-half kernel mapping (0xFFFF_FFFF_8000_0000)
- [ ] Page fault handler

### Success Criteria
```ritz
@test @integration
test_page_mapping():
    phys = alloc_frame()
    virt = 0xDEAD_BEEF_0000

    map_page(virt, phys, PRESENT | WRITABLE)

    # Write through virtual address
    store_u64(virt as ptr[u64], 0x12345678)

    # Read through physical (identity mapped in test)
    assert load_u64(phys as ptr[u64]) == 0x12345678

    unmap_page(virt)
```

---

## Milestone 5: APIC & Interrupts
**Goal**: Timer interrupts and interrupt routing

### Deliverables
- [ ] Detect and initialize Local APIC
- [ ] Configure APIC timer
- [ ] Handle timer interrupts
- [ ] IOAPIC setup for external interrupts
- [ ] Interrupt enable/disable primitives

### Success Criteria
```ritz
@test @integration
test_timer_interrupt():
    timer_count = 0

    install_handler(IRQ_TIMER, lambda: timer_count += 1)
    apic_start_timer(1000)  # 1ms interval
    enable_interrupts()

    sleep_busy(10)  # Wait ~10ms

    assert timer_count >= 9 and timer_count <= 11
```

---

## Milestone 6: Kernel Heap
**Goal**: Dynamic memory allocation in kernel

### Deliverables
- [ ] Heap region setup (after kernel BSS)
- [ ] `kalloc(size) -> ptr[u8]`
- [ ] `kfree(ptr)`
- [ ] Slab allocator for common sizes
- [ ] Heap corruption detection (debug mode)

### Success Criteria
```ritz
@test
test_heap_alloc():
    p1 = kalloc(64)
    p2 = kalloc(128)

    assert p1 != p2
    assert p2 > p1  # Sequential allocation

    kfree(p1)

    p3 = kalloc(32)
    assert p3 == p1  # Reuses freed block
```

---

## Milestone 7: Process Management (Kernel Threads)
**Goal**: Multiple kernel threads with preemptive scheduling

### Deliverables
- [ ] Thread structure (`Thread` with stack, registers, state)
- [ ] Context switching (save/restore all registers)
- [ ] Round-robin scheduler
- [ ] `spawn_thread(entry, arg)`
- [ ] `yield_thread()`
- [ ] Thread termination

### Success Criteria
```ritz
@test @integration
test_thread_scheduling():
    results: List[u32] = []

    thread_a():
        for i in range(3):
            results.push(1)
            yield_thread()

    thread_b():
        for i in range(3):
            results.push(2)
            yield_thread()

    spawn_thread(thread_a)
    spawn_thread(thread_b)
    scheduler_run()

    # Interleaved execution
    assert results == [1, 2, 1, 2, 1, 2]
```

---

## Milestone 8: User Space
**Goal**: Ring 3 processes with syscall interface

### Deliverables
- [ ] User-space page tables (USER flag)
- [ ] Ring 3 entry via `sysret`
- [ ] Syscall handler (`syscall` instruction)
- [ ] Basic syscalls: `exit`, `write`, `yield`
- [ ] ELF loader for user programs

### Success Criteria
```ritz
# user/hello.ritz
main():
    sys_write(1, "Hello from user space!\n", 23)
    sys_exit(0)
```

```bash
$ make run
...
Hello from Harland!       # Kernel
Hello from user space!    # User process
```

---

## Milestone 9: Syscall Abstraction Layer (CRITICAL)
**Goal**: Portable syscall interface for Ritz runtime

This is the key architectural piece that lets Ritz run on multiple kernels.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Ritz Application                           │
│                                                                 │
│    std::io::print("Hello")                                      │
│              │                                                  │
└──────────────┼──────────────────────────────────────────────────┘
               │
       ┌───────▼───────┐
       │  ritz::sys    │  ◄── Platform-agnostic syscall API
       │               │
       │  sys_write()  │
       │  sys_read()   │
       │  sys_mmap()   │
       │  sys_exit()   │
       └───────┬───────┘
               │
       ┌───────▼───────────────────────────────────────────┐
       │              Platform Backends                     │
       │                                                    │
       │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
       │  │ Harland │ │  Linux  │ │ Windows │ │  macOS  │  │
       │  │ Backend │ │ Backend │ │ Backend │ │ Backend │  │
       │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
       │       │           │           │           │        │
       └───────┼───────────┼───────────┼───────────┼────────┘
               │           │           │           │
          ┌────▼────┐ ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
          │ syscall │ │syscall()│ │NtWrite..│ │syscall()│
          │   0x80  │ │(Linux)  │ │(NT API) │ │(Darwin) │
          └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### Ritz Syscall API

```ritz
# ritz/sys/mod.ritz - Platform-agnostic syscall interface

# File descriptor operations
sys_read(fd: i32, buf: ptr[u8], count: usize) -> isize
sys_write(fd: i32, buf: ptr[u8], count: usize) -> isize
sys_open(path: ptr[u8], flags: i32, mode: u32) -> i32
sys_close(fd: i32) -> i32

# Memory operations
sys_mmap(addr: ptr[void], len: usize, prot: i32, flags: i32, fd: i32, offset: i64) -> ptr[void]
sys_munmap(addr: ptr[void], len: usize) -> i32
sys_brk(addr: ptr[void]) -> ptr[void]

# Process operations
sys_exit(code: i32) -> !
sys_fork() -> i32
sys_exec(path: ptr[u8], argv: ptr[ptr[u8]], envp: ptr[ptr[u8]]) -> i32
sys_wait(status: ptr[i32]) -> i32
sys_getpid() -> i32

# Time operations
sys_nanosleep(req: ptr[TimeSpec], rem: ptr[TimeSpec]) -> i32
sys_clock_gettime(clock: i32, tp: ptr[TimeSpec]) -> i32

# IPC (Harland-specific, emulated on other platforms)
sys_send(port: u32, msg: ptr[Message]) -> i32
sys_recv(port: u32, msg: ptr[Message]) -> i32
```

### Backend Selection (Compile Time)

```ritz
# ritz/sys/backend.ritz

@cfg(target_os = "harland")
import ritz.sys.harland as backend

@cfg(target_os = "linux")
import ritz.sys.linux as backend

@cfg(target_os = "windows")
import ritz.sys.windows as backend

@cfg(target_os = "macos")
import ritz.sys.macos as backend

# All backends implement the same interface
sys_write(fd: i32, buf: ptr[u8], count: usize) -> isize:
    return backend.sys_write(fd, buf, count)
```

### Harland Backend

```ritz
# ritz/sys/harland.ritz - Harland kernel syscall interface

SYSCALL_WRITE: u64 = 1
SYSCALL_READ: u64 = 0
SYSCALL_EXIT: u64 = 60
# ... etc

sys_write(fd: i32, buf: ptr[u8], count: usize) -> isize:
    result: isize
    asm x86_64:
        mov rax, {SYSCALL_WRITE}
        mov rdi, {fd}
        mov rsi, {buf}
        mov rdx, {count}
        syscall
        mov {result}, rax
    return result
```

### Linux Backend

```ritz
# ritz/sys/linux.ritz - Linux syscall interface

# Linux syscall numbers (x86-64)
SYS_READ: u64 = 0
SYS_WRITE: u64 = 1
SYS_OPEN: u64 = 2
SYS_CLOSE: u64 = 3
SYS_MMAP: u64 = 9
SYS_EXIT: u64 = 60
# ... etc

sys_write(fd: i32, buf: ptr[u8], count: usize) -> isize:
    result: isize
    asm x86_64:
        mov rax, {SYS_WRITE}
        mov rdi, {fd}
        mov rsi, {buf}
        mov rdx, {count}
        syscall
        mov {result}, rax
    return result

# Convenience wrappers
sys_write6(fd: i32, buf: ptr[u8], count: usize,
           arg4: u64, arg5: u64, arg6: u64) -> isize:
    result: isize
    asm x86_64:
        mov rax, {SYS_WRITE}
        mov rdi, {fd}
        mov rsi, {buf}
        mov rdx, {count}
        mov r10, {arg4}
        mov r8, {arg5}
        mov r9, {arg6}
        syscall
        mov {result}, rax
    return result
```

### Success Criteria
```ritz
# Same code runs on all platforms
main():
    msg = "Hello, World!\n"
    sys_write(1, msg as ptr[u8], 14)
    sys_exit(0)
```

```bash
# Linux
$ ritzc --target x86_64-linux hello.ritz -o hello
$ ./hello
Hello, World!

# Harland (in QEMU)
$ ritzc --target x86_64-harland hello.ritz -o hello
$ make run-user PROG=hello
Hello, World!
```

---

## Milestone 10: VirtIO Network Driver
**Goal**: User-space network driver with IPC

### Deliverables
- [ ] VirtIO device discovery
- [ ] VirtIO ring buffer implementation
- [ ] Ethernet frame send/receive
- [ ] Network server process
- [ ] IPC for network requests

### Success Criteria
- Ping from host to QEMU guest works
- Basic TCP echo server in Ritz

---

## Milestone 11: Basic Filesystem
**Goal**: In-memory filesystem with VFS layer

### Deliverables
- [ ] VFS abstraction
- [ ] In-memory tmpfs
- [ ] File operations: open, read, write, close
- [ ] Directory operations: mkdir, readdir
- [ ] Mount points

---

## Milestone 12: Self-Hosting Milestone
**Goal**: Ritz compiler runs on Harland

### Deliverables
- [ ] Python interpreter in Ritz (or native Ritz compiler)
- [ ] Filesystem access for source files
- [ ] Enough stdlib for compiler to work
- [ ] Compile a simple Ritz program on Harland

---

## Milestone Summary Table

| # | Milestone | Key Deliverable | Est. Complexity |
|---|-----------|-----------------|-----------------|
| 0 | Build Infra | `ritzc --target x86_64-none-elf` | Medium |
| 1 | Hello World | Serial output in QEMU | Low |
| 2 | Framebuffer | Graphical console | Medium |
| 3 | CPU Setup | GDT/IDT/Exceptions | Medium |
| 4 | Virtual Memory | Page tables | High |
| 5 | APIC | Timer interrupts | Medium |
| 6 | Kernel Heap | `kalloc`/`kfree` | Medium |
| 7 | Threads | Context switching | High |
| 8 | User Space | Ring 3, syscalls | High |
| **9** | **Syscall Abstraction** | **Portable Ritz runtime** | **High** |
| 10 | Networking | VirtIO NIC | High |
| 11 | Filesystem | VFS + tmpfs | Medium |
| 12 | Self-Hosting | Ritz on Harland | Very High |

---

## Testing Strategy

### Per-Milestone Testing

Each milestone has:
1. **Unit tests** - Run on host Linux, test pure functions
2. **Integration tests** - Run in QEMU, test hardware interaction
3. **Success criteria** - Automated validation

### CI Pipeline

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test-unit
  - test-qemu
  - test-multiplatform

build-kernel:
  stage: build
  script:
    - make kernel.elf bootloader.efi
    - make qcow2

test-unit:
  stage: test-unit
  script:
    - ritzc --target x86_64-linux --test kernel/**/*.ritz

test-qemu:
  stage: test-qemu
  script:
    - make test-qemu
  artifacts:
    paths:
      - test_output.log

test-linux:
  stage: test-multiplatform
  script:
    - ritzc --target x86_64-linux tests/syscall/*.ritz -o test_syscall
    - ./test_syscall

test-windows:
  stage: test-multiplatform
  tags: [windows]
  script:
    - ritzc --target x86_64-windows tests/syscall/*.ritz -o test_syscall.exe
    - ./test_syscall.exe
```

---

## Architecture Diagram (Full Vision)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Ritz Applications                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   CLI    │  │   GUI    │  │  Server  │  │  Games   │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       └─────────────┴────────────┬┴──────────────┘                  │
├──────────────────────────────────┼──────────────────────────────────┤
│                                  │                                  │
│  ┌───────────────────────────────▼───────────────────────────────┐  │
│  │                     Ritz Standard Library                     │  │
│  │                                                               │  │
│  │   std::io    std::fs    std::net    std::thread   std::mem    │  │
│  └───────────────────────────────┬───────────────────────────────┘  │
│                                  │                                  │
│  ┌───────────────────────────────▼───────────────────────────────┐  │
│  │                     ritz::sys (Syscall API)                   │  │
│  │                                                               │  │
│  │   sys_read  sys_write  sys_mmap  sys_fork  sys_exec  ...      │  │
│  └───────────────────────────────┬───────────────────────────────┘  │
│                                  │                                  │
├──────────────────────────────────┼──────────────────────────────────┤
│                    Platform Backends                                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │
│  │ Harland │  │  Linux  │  │ Windows │  │  macOS  │  │   ARM   │   │
│  │(native) │  │  (ELF)  │  │  (PE)   │  │(Mach-O) │  │(aarch64)│   │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘   │
│       │            │            │            │            │         │
└───────┼────────────┼────────────┼────────────┼────────────┼─────────┘
        │            │            │            │            │
   ┌────▼────┐  ┌────▼────┐  ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
   │ Harland │  │  Linux  │  │ Windows │  │  macOS  │  │  Linux  │
   │ Kernel  │  │ Kernel  │  │  NT     │  │  XNU    │  │  ARM64  │
   └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘
```

This is the end goal: **Write once in Ritz, run anywhere.**
