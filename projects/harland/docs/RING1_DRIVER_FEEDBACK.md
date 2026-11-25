# Review feedback for the Harland ring-1 driver design

This review covers [RING1_DRIVER.md](RING1_DRIVER.md) at `a92ac7d2`. The CPL-1 selectors, `iretq` return model, and distinction between TSS `rsp0` and IST are consistent with the current kernel. Keep the ring-2 stack as the eventual consumer and the kernel as the first consumer. Address the following before landing the driver ABI or cutting over virtio-net.

## Required changes

### 1. Make per-device DMA domains part of the first cutover

The driver can program queue addresses through virtio common configuration. Write access to those registers gives the NIC access to whatever its requester can DMA to. A CPU-side BAR allowlist and CPL-1 page tables cannot keep the NIC out of framebuffer memory, kernel memory, or another device's buffers. Harland currently has VT-d DMA translation disabled and AMD-Vi configured for DMA passthrough. [VT-d implementation](../kernel/src/drivers/iommu/vtd.ritz#L26) · [AMD-Vi implementation](../kernel/src/drivers/iommu/amdvi.ritz#L16)

- Require a private, translated DMA domain for the NIC before granting queue-programming access or enabling bus mastering for the driver. Identify the requester by PCI segment and device identity, account for DMA aliases, and refuse the cutover if the requester cannot be isolated. Define the unsupported-hardware and boot-test behavior explicitly.
- Map only explicitly granted queue and packet pages into that domain. Keep the CPU-only frame rings, framebuffer, and unrelated RAM outside it. Specify device access permissions and return a device-visible DMA address or IOVA from `DrvDmaAlloc`. State the lifetime of each mapping and include translation invalidation in teardown.
- Add the DMA-domain work to the PR dependencies ahead of writable BAR grants and the NIC cutover. Add an acceptance check that the NIC can use its allocated buffers while the framebuffer and other ungranted pages have no mapping in its domain.

### 2. Protect device and shared mappings through teardown

The draft excludes driver windows from `mmap`, but ordinary `munmap` still accepts addresses in those windows and frees the returned physical pages. Protect the complete reserved ranges from generic unmap, including requests that start outside and overlap those ranges. Define cleanup for partially installed mappings and clear or initialize DMA pages before granting access. [Draft mapping rules](RING1_DRIVER.md#5-mmio-and-dma-syscalls) · [Current munmap](../kernel/src/syscall/runtime/memory.ritz#L299)

On driver exit, revoke access to the shared rings and wake the consumer. Mask device interrupts and complete device quiescence and DMA-domain teardown before PMM reuse. A virtio status-zero write initiates a reset. Use the status readback to establish completion, and keep pages reserved if reset or DMA revocation cannot be confirmed. Specify who owns pages in that failure path. [Draft death path](RING1_DRIVER.md#driver-death) · [Virtio 1.2 device reset](https://docs.oasis-open.org/virtio/virtio/v1.2/virtio-v1.2.html#x1-150004)

### 3. Keep the network self-test bounded and schedule both endpoints

The DHCP loop checks the overall deadline and the deferred gateway ping only after `net_wait_rx` returns. The proposed `BLOCK_RING` wait has no timeout, so a quiet link can stall either check. Give the receive wait a deadline or another defined time wakeup. Cover an idle link and a link that stops delivering frames after DHCP. [Draft RX wait](RING1_DRIVER.md#6-portable-spsc-ring) · [Current DHCP loop](../kernel/src/postinit.ritz#L403)

The TX burst polls with interrupts disabled. A group of four sends can fit in the 256-slot ring, so publishing those frames need never reach the full-ring yield. The kernel can run through the reply polls while the driver gets no CPU time. Make the burst explicitly schedule the driver while awaiting replies, and keep the existing 300-send and distinct-reply assertions. [Current burst](../kernel/src/postinit.ritz#L340)

### 4. Define page-granular MMIO grants

Virtio PCI capability ranges are byte-sized and can share a page. Requiring page-aligned requests entirely within the byte range can reject supported hardware. Rounding outward without checking adjacent registers can expose the MSI-X table or other protected registers. Define grants in terms of complete pages, preserve the register offsets and notify multiplier in the spawn handoff, and specify how the kernel refuses or mediates a page that overlaps protected registers. [Draft MMIO grant](RING1_DRIVER.md#5-mmio-and-dma-syscalls) · [Current capability probe](../kernel/src/drivers/virtio/common.ritz#L668)

### 5. Build the syscall return frame on the kernel stack

The proposed selector substitution retains the existing `popq %rsp` before the frame pushes. This leaves CPL 0 building the frame through a process-controlled stack pointer, so an invalid user stack can fault in the kernel return path. Build the complete frame on the kernel stack and let `iretq` restore the saved user RSP. Test both CPL-1 and CPL-3 returns, including an invalid saved user stack. [Draft process entry](RING1_DRIVER.md#2-process-entry-and-the-driver-mark) · [Current return assembly](../kernel/syscall_entry.s#L291)

## ABI details to settle before freezing the layout

- **Frame validation.** Specify how the kernel handles peer-written lengths, indices, and invalid occupancy. Derive offsets from the slot where possible, and validate bounds before copying or dispatching a frame. This remains necessary with DMA isolation because the driver can still write the shared CPU mappings. [Frame protocol](RING1_DRIVER.md#6-portable-spsc-ring)
- **Link publication.** Zeroed memory starts with `link_seq == 0`, and even values are described as stable. Define a distinct unpublished state and the full writer and reader protocol. A kernel-owned snapshot updated through an explicit publish operation is one option for the current BSP-only design. Both syscall 60 and the in-kernel consumer need a defined snapshot and behavior before publication and after death. [Syscall 60](RING1_DRIVER.md#7-syscall-60)
- **Portable wake and layout.** Linux classic futex operations use a 32-bit word. Windows `WakeByAddressSingle` is process-local, so use a cross-process primitive such as a shared event handle with an explicit recheck protocol. Specify the exact offsets and total size. Individually page-aligning both controls, both descriptor arrays, and the link record adds five pages to the 1 MiB arenas. The proposed three-page overhead requires packing the controls and record onto a single page. [Draft layout](RING1_DRIVER.md#6-portable-spsc-ring) · [Linux futex documentation](https://kernel.org/doc/html/v6.8/userspace-api/futex2.html) · [Windows wake API documentation](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-wakebyaddresssingle)
