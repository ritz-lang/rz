# LARB Proposal: Harland Virtualization Architecture

**Proposal ID:** LARB-2025-001
**Status:** Draft
**Author:** Claude (AI Assistant)
**Date:** 2025-02-15
**Review Requested:** Yes

---

## Executive Summary

This proposal outlines a virtualization architecture for Harland that leverages its microkernel design to enable:

1. **Nested Harland instances** - Running isolated Harland VMs inside Harland
2. **Live code editing** - "Build the airplane while flying" up to Ring 1
3. **Hardware-assisted isolation** - Intel VT-x/AMD-V for strong security boundaries

The microkernel architecture makes this surprisingly tractable since all services above Ring 0 are already isolated processes with capability-mediated resource access.

---

## Motivation

### Use Cases

1. **Development Environment**
   - Test kernel changes in isolated VM without rebooting host
   - Hot-reload Ring 1/2 services during development
   - Snapshot/restore for debugging

2. **Production Isolation**
   - Multi-tenant hosting with strong isolation
   - Per-service VMs for security-critical workloads
   - Resource quotas enforced at hypervisor level

3. **Live Patching**
   - Update Ring 1 services without restarting Ring 0
   - Zero-downtime kernel module updates
   - Gradual rollout with instant rollback

4. **Capability Composition**
   - Grant a VM a restricted capability set
   - Compose multiple VMs' capabilities into a unified namespace
   - Capability delegation across VM boundaries

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Ring 3: Applications                                             │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│ │  App A   │ │  App B   │ │  App C   │ │  Nested Harland VM   │ │
│ └──────────┘ └──────────┘ └──────────┘ │ ┌────────────────┐   │ │
│                                         │ │ Guest Ring 3   │   │ │
│                                         │ │  ┌──────────┐  │   │ │
│                                         │ │  │ Guest App│  │   │ │
│                                         │ │  └──────────┘  │   │ │
├─────────────────────────────────────────│─┼────────────────┼───┤ │
│ Ring 2: Drivers & Services              │ │ Guest Ring 2   │   │ │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ │ │  Goliath FS    │   │ │
│ │ Goliath  │ │  NetSvc  │ │ InputSvc │ │ └────────────────┘   │ │
│ │   FS     │ │          │ │          │ │ Guest Ring 1        │ │
│ └──────────┘ └──────────┘ └──────────┘ │  VirtIO drivers     │ │
├─────────────────────────────────────────│─────────────────────┤ │
│ Ring 1: Hardware Abstraction            │ Guest Ring 0        │ │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ │ ┌────────────────┐   │ │
│ │ VirtIO   │ │  ACPI    │ │   USB    │ │ │ Guest Kernel   │   │ │
│ │ Drivers  │ │          │ │          │ │ └────────────────┘   │ │
│ └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ Ring 0: Harland Microkernel                                     │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│ │Capability│ │   IPC    │ │ Scheduler│ │     VMM / VT-x       │ │
│ │  Tables  │ │ Channels │ │          │ │   Hypervisor Core    │ │
│ └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Hypervisor Core (Ring 0)

The hypervisor is a Ring 0 kernel module that manages:

- **VMCS (Virtual Machine Control Structure)** - Per-VM state
- **EPT (Extended Page Tables)** - Guest physical → host physical mapping
- **VM Entry/Exit handling** - Trap sensitive operations
- **Virtual device emulation** - Expose VirtIO devices to guests

```ritz
struct VirtualMachine
    vmcs_phys: u64              # Physical address of VMCS
    ept_pml4: u64               # Guest EPT root
    guest_state: VmGuestState   # Saved registers on VM exit
    caps: CapTable              # Capabilities granted to this VM
    vcpus: [MAX_VCPUS]Vcpu      # Virtual CPUs
    memory_regions: Vec<VmMemoryRegion>
    devices: Vec<VmDevice>
```

#### 2. Capability-Based VM Access

VMs are just another resource type with capabilities:

```ritz
const CAP_TYPE_VM: u32 = 12

# VM-specific rights
const CAP_VM_START: u64    = 0x001   # Start/stop the VM
const CAP_VM_PAUSE: u64    = 0x002   # Pause/resume
const CAP_VM_MEMORY: u64   = 0x004   # Map guest memory
const CAP_VM_VCPU: u64     = 0x008   # Control vCPUs
const CAP_VM_DEVICE: u64   = 0x010   # Attach/detach devices
const CAP_VM_SNAPSHOT: u64 = 0x020   # Create snapshots
const CAP_VM_MIGRATE: u64  = 0x040   # Live migration
```

A process with `CAP_VM_MEMORY` can map guest physical memory into its address space, enabling:
- Guest memory inspection
- DMA to guest buffers
- Shared memory between host and guest

#### 3. VirtIO Para-virtualization

Guests see VirtIO devices backed by host resources:

| Guest Device | Host Backend |
|--------------|--------------|
| virtio-blk   | Host file or block device |
| virtio-net   | Host network interface or tap |
| virtio-console | Host serial port or PTY |
| virtio-fs    | Host Goliath filesystem |

This allows **transparent capability delegation**:
- Host grants guest a `CAP_TYPE_FILE` for a directory
- Guest sees it as a virtio-fs mount
- Guest applications use normal FS syscalls

---

## Live Code Editing Architecture

### Hot-Reload Levels

| Level | What Can Change | Mechanism | Downtime |
|-------|-----------------|-----------|----------|
| Ring 3 | Applications | Process restart | Per-app |
| Ring 2 | FS/Network services | Service restart | Per-service |
| Ring 1 | Device drivers | Module reload | Brief pause |
| Ring 0 | Kernel core | **VM checkpoint** | VM only |

### Ring 0 Live Patching via VM Checkpoint

The key insight: we can update Ring 0 code by:

1. **Checkpoint** the current VM state (including all processes)
2. **Boot** a new kernel with the patch
3. **Restore** the VM state on the new kernel
4. **Verify** integrity before committing

```
┌────────────────────────────────────────────────────────────────┐
│  Old Kernel v1.0                    New Kernel v1.1            │
│  ┌──────────────┐                   ┌──────────────┐           │
│  │ Running VMs  │ ──checkpoint──>   │   Restore    │           │
│  │ + All State  │                   │  VMs + State │           │
│  └──────────────┘                   └──────────────┘           │
│         │                                  │                    │
│         v                                  v                    │
│  ┌──────────────┐                   ┌──────────────┐           │
│  │ Kernel v1.0  │                   │ Kernel v1.1  │           │
│  └──────────────┘                   └──────────────┘           │
│         │                                  │                    │
│         └──────── verify ────────────────>│                    │
│                                            │                    │
│  If verify fails: restore v1.0 checkpoint  │                    │
│  If verify passes: commit, discard v1.0    │                    │
└────────────────────────────────────────────────────────────────┘
```

### Ring 1 Driver Hot-Reload

Device drivers in Ring 1 can be reloaded without affecting other services:

1. Quiesce the device (drain pending I/O)
2. Save driver state to shared memory
3. Unload old driver module
4. Load new driver module
5. Restore state from shared memory
6. Resume device operations

The capability system ensures:
- Only authorized processes can reload drivers
- The new driver inherits exactly the old driver's capabilities
- Revocation is instant if the new driver misbehaves

---

## initramfs Architecture

### Two-Disk Model

```
┌─────────────────────────────────────────────────────────────────┐
│                        Boot Process                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ initramfs.qcow2 (read-only, versioned)                   │   │
│  │                                                          │   │
│  │  /drivers/                                               │   │
│  │    virtio_blk.ko   # Block device driver                 │   │
│  │    virtio_net.ko   # Network driver                      │   │
│  │    goliath.ko      # Filesystem driver                   │   │
│  │                                                          │   │
│  │  /services/                                              │   │
│  │    netd            # Network daemon                      │   │
│  │    fsd             # Filesystem daemon                   │   │
│  │    init            # PID 1                               │   │
│  │                                                          │   │
│  │  /config/                                                │   │
│  │    boot.toml       # Boot configuration                  │   │
│  │    services.toml   # Service dependencies                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            v                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ storage.qcow2 (read-write, user data)                    │   │
│  │                                                          │   │
│  │  /home/           # User files                           │   │
│  │  /var/            # Variable data                        │   │
│  │  /etc/            # Local configuration (overlay)        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Overlay Filesystem

The initramfs is read-only but can be "modified" via overlay:

```
Final view = initramfs (lower) + storage:/overlays/initramfs (upper)
```

This allows:
- Local configuration overrides
- Temporary patches without rebuilding initramfs
- Instant rollback by clearing overlay

### initramfs Versioning

Each initramfs has a version and signature:

```toml
# /config/boot.toml
[initramfs]
version = "2025.02.15-abc123"
signature = "sha256:..."
rollback_to = "2025.02.14-xyz789"
```

On boot failure, the bootloader can:
1. Detect the failure (watchdog, explicit signal)
2. Rollback to previous initramfs version
3. Log the failure for analysis

---

## Implementation Phases

### Phase 1: VT-x Foundation (4-6 weeks)

- [ ] Detect and enable VT-x/AMD-V
- [ ] Implement VMCS management
- [ ] Basic VM entry/exit handling
- [ ] EPT setup and TLB management
- [ ] Simple "hello world" guest

### Phase 2: Device Emulation (4-6 weeks)

- [ ] VirtIO device framework for guests
- [ ] virtio-console for guest serial
- [ ] virtio-blk backed by host file
- [ ] Guest interrupt injection

### Phase 3: Full Guest Support (4-6 weeks)

- [ ] Boot full Harland guest
- [ ] Multi-vCPU support
- [ ] Guest memory ballooning
- [ ] VM checkpoint/restore

### Phase 4: Live Patching (4-6 weeks)

- [ ] Ring 1 driver hot-reload
- [ ] Ring 2 service hot-reload
- [ ] Ring 0 VM-based patching
- [ ] Rollback mechanisms

### Phase 5: initramfs (2-4 weeks)

- [ ] Goliath filesystem integration
- [ ] Boot from initramfs
- [ ] Overlay filesystem
- [ ] Versioned images

---

## Security Considerations

### Threat Model

1. **Malicious Guest** - Guest VM tries to escape to host
   - Mitigation: VT-x hardware isolation, EPT enforcement

2. **Malicious Driver** - Hot-reloaded driver is compromised
   - Mitigation: Capability-limited scope, signature verification

3. **initramfs Tampering** - Attacker modifies boot image
   - Mitigation: Cryptographic signatures, TPM-based attestation

4. **VM-to-VM Attack** - Guest A attacks Guest B
   - Mitigation: Complete memory isolation via EPT, no shared pages without explicit grant

### Required Hardware

| Feature | Intel | AMD | Required For |
|---------|-------|-----|--------------|
| VT-x / AMD-V | Yes | Yes | Basic virtualization |
| EPT / NPT | Yes | Yes | Guest memory isolation |
| VMCS shadowing | Optional | N/A | Nested virtualization |
| Posted interrupts | Optional | N/A | Performance |

---

## Open Questions for LARB

1. **Ring 0 patching granularity** - Should we support function-level patching, or only full kernel replacement?

2. **Capability inheritance** - When a VM is checkpointed and restored on a new kernel, how do we handle capability table migration?

3. **Resource limits** - Should VMs have hard memory/CPU limits enforced by the hypervisor, or rely on guest cooperation?

4. **Nested virtualization** - Should we support running VMs inside VMs? (Significantly more complex)

5. **GPU virtualization** - VirtIO-GPU for guests, or passthrough via IOMMU?

---

## References

- Intel SDM Vol. 3C, Chapter 23-33 (VMX)
- AMD APM Vol. 2, Chapter 15 (SVM)
- VirtIO Specification v1.2
- seL4 Virtualization Design
- Xen Hypervisor Architecture

---

## Approval

- [ ] LARB Review Scheduled
- [ ] Technical Review Complete
- [ ] Security Review Complete
- [ ] Approved for Implementation

---

*This proposal was drafted by Claude (AI Assistant) based on discussions with Aaron Sinclair about Harland's virtualization roadmap.*
