# Harland Subsystem Design

High-level design for Harland's user-space subsystems. These run as isolated processes with capability-based access to kernel resources.

> **Note:** This document lives in LARB as reference architecture. Harland will maintain its own detailed implementation docs.

---

## Overview

Harland follows a microkernel architecture where drivers run in user space:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Space                                      │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────┐ │
│  │  GPU      │ │   USB     │ │  Storage  │ │  Network  │ │    Input      │ │
│  │  Driver   │ │  Stack    │ │  Driver   │ │  Stack    │ │   Driver      │ │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └───────┬───────┘ │
│        │             │             │             │               │         │
│        └─────────────┴─────────────┴─────────────┴───────────────┘         │
│                                    │                                        │
│                        ┌───────────▼───────────┐                           │
│                        │    Device Manager     │                           │
│                        │   (capability broker) │                           │
│                        └───────────┬───────────┘                           │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │ (kernel caps)
┌────────────────────────────────────▼────────────────────────────────────────┐
│                           Harland Kernel                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────────────────┐ │
│  │  Interrupt  │ │   Memory    │ │     IPC     │ │   Capability Tables    │ │
│  │  Dispatch   │ │   Manager   │ │             │ │                        │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Capability Model

All subsystems access hardware via capabilities granted by the kernel.

### Capability Types

| Capability | Grants Access To |
|------------|------------------|
| `IoPort(base, count)` | Port I/O range |
| `MmioRegion(addr, size)` | Memory-mapped I/O region |
| `Irq(number)` | Interrupt line |
| `DmaBuffer(addr, size)` | DMA-capable memory |
| `IpcEndpoint(id)` | Communication channel |

### Capability Operations

```ritz
# Capabilities are unforgeable tokens
struct Capability
    id: u64           # Kernel-assigned ID
    type: CapType     # What it grants
    rights: Rights    # Read, write, delegate, etc.

# Operations
fn cap_invoke(cap: Capability, args: CapArgs) -> Result<CapResult, CapError>
fn cap_delegate(cap: Capability, target: ProcessId, attenuate: Rights) -> Result<Capability, CapError>
fn cap_revoke(cap: Capability) -> Result<(), CapError>
```

---

## GPU Subsystem

### Overview

Provides display output via virtio-gpu (QEMU development target), with future hardware GPU support.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Prism (Display Server)           │
│           (window management, compositing)          │
└───────────────────────────┬─────────────────────────┘
                            │ (buffer sharing)
┌───────────────────────────▼─────────────────────────┐
│                    GPU Driver                        │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐ │
│  │ Command     │ │ Framebuffer │ │ Resource       │ │
│  │ Submission  │ │ Management  │ │ Allocation     │ │
│  └─────────────┘ └─────────────┘ └────────────────┘ │
└───────────────────────────┬─────────────────────────┘
                            │ (virtio protocol)
┌───────────────────────────▼─────────────────────────┐
│                  virtio-gpu device                   │
└─────────────────────────────────────────────────────┘
```

### Capabilities Required

- `MmioRegion` for virtio config space
- `Irq` for completion notifications
- `DmaBuffer` for command queues and framebuffers

### Key Interfaces

```ritz
trait GpuDriver
    fn create_framebuffer(width: u32, height: u32, format: PixelFormat) -> Result<Framebuffer, GpuError>
    fn present(fb: Framebuffer) -> Result<(), GpuError>
    fn create_context() -> Result<GpuContext, GpuError>
    fn submit_commands(ctx: GpuContext, cmds: CommandBuffer) -> Result<Fence, GpuError>
```

---

## USB Subsystem

### Overview

USB stack with host controller abstraction, supporting virtio-usb for development and future xHCI for real hardware.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                   USB Class Drivers                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│  │   HID   │ │ Storage │ │  Audio  │ │  Network  │ │
│  │(kb/mouse)│ │ (MSC)   │ │ (UAC)   │ │  (CDC)    │ │
│  └────┬────┘ └────┬────┘ └────┬────┘ └─────┬─────┘ │
└───────┴───────────┴───────────┴─────────────┴───────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│                    USB Core                          │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐ │
│  │ Device      │ │ Endpoint    │ │ Transfer       │ │
│  │ Enumeration │ │ Management  │ │ Scheduling     │ │
│  └─────────────┘ └─────────────┘ └────────────────┘ │
└───────────────────────────┬─────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│              Host Controller Driver                  │
│  ┌─────────────────┐     ┌────────────────────────┐ │
│  │   virtio-usb    │     │   xHCI (future)        │ │
│  │   (development) │     │   (real hardware)      │ │
│  └─────────────────┘     └────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Capabilities Required

- `MmioRegion` for controller registers
- `Irq` for transfer completions
- `DmaBuffer` for transfer descriptors and data

### Key Interfaces

```ritz
trait UsbDevice
    fn get_descriptor(desc_type: DescriptorType) -> Result<Descriptor, UsbError>
    fn set_configuration(config: u8) -> Result<(), UsbError>
    fn control_transfer(setup: SetupPacket, data: Option<&[u8]>) -> Result<usize, UsbError>
    fn bulk_transfer(endpoint: u8, data:& [u8]) -> Result<usize, UsbError>
```

---

## Storage Subsystem

### Overview

Block device abstraction with virtio-blk for development, supporting the Goliath filesystem.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Applications                      │
└───────────────────────────┬─────────────────────────┘
                            │ (POSIX-like API)
┌───────────────────────────▼─────────────────────────┐
│                  VFS (Virtual File System)           │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐ │
│  │   Goliath   │ │    tmpfs    │ │   devfs        │ │
│  │ (content-   │ │ (in-memory) │ │ (device nodes) │ │
│  │  addressed) │ │             │ │                │ │
│  └─────────────┘ └─────────────┘ └────────────────┘ │
└───────────────────────────┬─────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│                Block Device Layer                    │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐ │
│  │ Request     │ │ Scheduler   │ │ Cache          │ │
│  │ Queue       │ │ (elevator)  │ │ (page cache)   │ │
│  └─────────────┘ └─────────────┘ └────────────────┘ │
└───────────────────────────┬─────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│              Block Device Drivers                    │
│  ┌─────────────────┐     ┌────────────────────────┐ │
│  │   virtio-blk    │     │   NVMe (future)        │ │
│  └─────────────────┘     └────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Key Interfaces

```ritz
trait BlockDevice
    fn read_blocks(start: u64, count: u32, buf:& [u8]) -> Result<(), BlockError>
    fn write_blocks(start: u64, count: u32, buf: [u8]) -> Result<(), BlockError>
    fn flush() -> Result<(), BlockError>
    fn block_size() -> u32
    fn block_count() -> u64
```

---

## Network Subsystem

### Overview

Full TCP/IP stack in user space, with virtio-net for development.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Applications                      │
│             (Valet, Tempest, user apps)               │
└───────────────────────────┬─────────────────────────┘
                            │ (socket API)
┌───────────────────────────▼─────────────────────────┐
│                    Socket Layer                      │
│         (TCP, UDP, raw sockets, Unix domain)         │
└───────────────────────────┬─────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│                   TCP/IP Stack                       │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐ │
│  │    TCP      │ │    UDP      │ │    ICMP        │ │
│  └─────────────┘ └─────────────┘ └────────────────┘ │
│  ┌─────────────┐ ┌─────────────┐                    │
│  │     IP      │ │    ARP      │                    │
│  └─────────────┘ └─────────────┘                    │
└───────────────────────────┬─────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│              Network Device Drivers                  │
│  ┌─────────────────┐     ┌────────────────────────┐ │
│  │   virtio-net    │     │   e1000/igb (future)   │ │
│  └─────────────────┘     └────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Capabilities Required

- `MmioRegion` for NIC registers
- `Irq` for packet notifications
- `DmaBuffer` for packet buffers and descriptor rings

---

## Input Subsystem

### Overview

Handles keyboard, mouse, and touch input via virtio-input.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Prism (Display Server)            │
│              (input focus, event routing)            │
└───────────────────────────┬─────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│                   Input Manager                      │
│  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐ │
│  │  Keyboard   │ │   Mouse     │ │   Touchscreen  │ │
│  │  Handler    │ │   Handler   │ │   Handler      │ │
│  └─────────────┘ └─────────────┘ └────────────────┘ │
└───────────────────────────┬─────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────┐
│              Input Device Drivers                    │
│  ┌─────────────────────────────────────────────────┐│
│  │               virtio-input                       ││
│  │   (keyboard, mouse, tablet events)               ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

### Key Interfaces

```ritz
enum InputEvent
    KeyPress { code: KeyCode, modifiers: Modifiers }
    KeyRelease { code: KeyCode, modifiers: Modifiers }
    MouseMove { x: i32, y: i32 }
    MouseButton { button: Button, pressed: bool }
    Scroll { dx: i32, dy: i32 }
    Touch { id: u32, x: i32, y: i32, pressure: f32 }

trait InputHandler
    fn handle_event(event: InputEvent)
```

---

## Device Manager

The Device Manager is a privileged user-space process that:

1. **Discovers devices** via device tree or ACPI
2. **Loads drivers** and grants them appropriate capabilities
3. **Mediates access** between applications and drivers
4. **Handles hotplug** events (USB, etc.)

### Capability Brokering

```
Application                 Device Manager                Driver
    │                             │                          │
    │ ──request_access(device)──► │                          │
    │                             │ ──check_policy()──►      │
    │                             │ ◄──allow/deny────        │
    │                             │                          │
    │                             │ ──delegate_cap(attenuated)──►
    │ ◄──capability_token──       │                          │
    │                             │                          │
    │ ─────────invoke_capability──────────────────────────►  │
```

---

## Security Considerations

### Isolation Guarantees

1. **Driver isolation**: Drivers cannot access memory outside their granted regions
2. **No ambient authority**: All access requires explicit capabilities
3. **Revocable access**: Capabilities can be revoked (e.g., on device disconnect)
4. **Audit trail**: Capability operations can be logged

### Attack Surface Reduction

- Drivers run as unprivileged user-space processes
- Only the Device Manager has capability creation rights
- Applications can't directly touch hardware

---

## Future Hardware Targets

| Subsystem | Development (virtio) | Future Hardware |
|-----------|---------------------|-----------------|
| GPU | virtio-gpu | Intel/AMD/NVIDIA (DRM) |
| USB | virtio-usb | xHCI, EHCI |
| Storage | virtio-blk | NVMe, AHCI |
| Network | virtio-net | Intel e1000/igb, Realtek |
| Input | virtio-input | PS/2, USB HID (via USB stack) |

---

*This document provides high-level architecture for reference. See Harland's implementation docs for details.*
