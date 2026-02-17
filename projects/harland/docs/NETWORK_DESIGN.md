# Harland Network Subsystem Design

## Philosophy

**No concessions.** We build the network stack properly from the start.

The goal isn't just "ping 1.1.1.1" - it's building a proper network subsystem that can grow into TCP, UDP sockets, and eventually a full networking API. The architecture must support the multi-ring model from day one.

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Ring 3 - User Applications                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │    ping     │  │   netstat   │  │    shell    │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
│         │                │                │                         │
│         └────────────────┼────────────────┘                         │
│                          │ syscalls / IPC                           │
├──────────────────────────┼──────────────────────────────────────────┤
│  Ring 2 - Network Stack Service (netd)                              │
│               ┌──────────▼──────────┐                               │
│               │     net/stack.ritz   │                              │
│               │  ┌────────────────┐ │                               │
│               │  │   net/icmp     │ │  ICMP echo/reply              │
│               │  │   net/udp      │ │  UDP datagrams                │
│               │  │   net/tcp      │ │  TCP streams (future)         │
│               │  ├────────────────┤ │                               │
│               │  │   net/ip       │ │  IPv4 routing                 │
│               │  ├────────────────┤ │                               │
│               │  │   net/arp      │ │  ARP resolution               │
│               │  │   net/eth      │ │  Ethernet framing             │
│               │  └────────────────┘ │                               │
│               └──────────┬──────────┘                               │
│                          │ IPC channel                              │
├──────────────────────────┼──────────────────────────────────────────┤
│  Ring 1 - NIC Driver (virtio-netd)                                  │
│               ┌──────────▼──────────┐                               │
│               │ drivers/virtio/net  │                               │
│               │  • VirtIO queues    │                               │
│               │  • DMA buffers      │                               │
│               │  • TX/RX            │                               │
│               └──────────┬──────────┘                               │
│                          │ capabilities (IOPORT, IRQ, DMA)          │
├──────────────────────────┼──────────────────────────────────────────┤
│  Ring 0 - Microkernel                                               │
│               ┌──────────▼──────────┐                               │
│               │  • IRQ dispatch     │                               │
│               │  • Page tables      │                               │
│               │  • IPC primitives   │                               │
│               │  • Capability mgmt  │                               │
│               └─────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

Following the established pattern (see `drivers/virtio/blk.ritz`):

```
kernel/src/
├── drivers/
│   └── virtio/
│       ├── common.ritz     # Shared VirtIO primitives (exists)
│       ├── blk.ritz        # Block driver (exists, pattern to follow)
│       └── net.ritz        # Network driver (NEW)
│
└── net/                     # Network subsystem (NEW)
    ├── types.ritz          # Shared types, constants, byte order
    ├── eth.ritz            # Ethernet layer (L2)
    ├── arp.ritz            # ARP protocol
    ├── ip.ritz             # IPv4 layer (L3)
    ├── icmp.ritz           # ICMP protocol
    ├── udp.ritz            # UDP protocol (L4)
    ├── route.ritz          # Routing table
    ├── stack.ritz          # Main network stack (init, poll, dispatch)
    └── syscall.ritz        # Network syscalls for userspace
```

---

## Code Extraction Plan

### From main.ritz → drivers/virtio/net.ritz

The VirtIO network driver (~400 lines):

```ritz
# drivers/virtio/net.ritz
#
# VirtIO Network Device Driver
#
# Handles low-level NIC operations:
# - Device initialization
# - DMA buffer management
# - Packet TX/RX via virtqueues

import drivers.virtio.common { ... }
import mm.vmm { vmm_virt_to_phys }
import serial { prints, serial_print_hex, serial_print_dec }

# VirtIO-Net Feature Bits
pub const VIRTIO_NET_F_CSUM: u32 = 0x0001
pub const VIRTIO_NET_F_MAC: u32 = 0x0020
pub const VIRTIO_NET_F_STATUS: u32 = 0x10000
# ... etc

# Device state
pub struct VirtioNetDevice
    pci_dev: *PciDevice
    io_base: u16
    rx_queue: VirtQueue
    tx_queue: VirtQueue
    features: u32
    mac: [6]u8
    initialized: u8

# Public API
pub fn virtio_net_init() -> i32
pub fn virtio_net_send(data: *u8, len: u32) -> i32
pub fn virtio_net_poll(buf: *u8, max_len: u32) -> i32
pub fn virtio_net_is_ready() -> u8
pub fn virtio_net_get_mac(mac_out: *u8)
```

### From main.ritz → net/types.ritz

Shared types and utilities (~50 lines):

```ritz
# net/types.ritz
#
# Common network types and byte-order conversions

# Byte order conversion (host ↔ network)
pub fn htons(val: u16) -> u16
pub fn ntohs(val: u16) -> u16
pub fn htonl(val: u32) -> u32
pub fn ntohl(val: u32) -> u32

# Protocol numbers
pub const IP_PROTO_ICMP: u8 = 1
pub const IP_PROTO_TCP: u8 = 6
pub const IP_PROTO_UDP: u8 = 17

# Ethertypes
pub const ETHERTYPE_IPV4: u16 = 0x0800
pub const ETHERTYPE_ARP: u16 = 0x0806
pub const ETHERTYPE_IPV6: u16 = 0x86DD
```

### From main.ritz → net/eth.ritz

Ethernet layer (~80 lines):

```ritz
# net/eth.ritz
#
# Ethernet frame handling (Layer 2)

import net.types { htons, ntohs, ETHERTYPE_IPV4, ETHERTYPE_ARP }

pub const ETH_HEADER_SIZE: u32 = 14
pub const ETH_MIN_FRAME: u32 = 60
pub const ETH_MAX_FRAME: u32 = 1514

pub struct EthHeader
    dst_mac: [6]u8
    src_mac: [6]u8
    ethertype: u16

pub fn eth_build_frame(buf: *u8, dst_mac: *u8, src_mac: *u8,
                       ethertype: u16, payload: *u8, payload_len: u32) -> u32

pub fn eth_parse_header(buf: *u8, header: *EthHeader)
```

### From main.ritz → net/arp.ritz

ARP protocol (~160 lines):

```ritz
# net/arp.ritz
#
# Address Resolution Protocol
# Maps IPv4 addresses to MAC addresses

import net.types { ... }
import net.eth { ... }

pub const ARP_OP_REQUEST: u16 = 1
pub const ARP_OP_REPLY: u16 = 2

pub struct ArpEntry
    ip: [4]u8
    mac: [6]u8
    valid: u8

# ARP cache (simple linear for now)
const ARP_CACHE_SIZE: i32 = 16
var arp_cache: [16]ArpEntry

pub fn arp_init()
pub fn arp_cache_lookup(ip: *u8, mac_out: *u8) -> i32
pub fn arp_cache_add(ip: *u8, mac: *u8)
pub fn arp_send_request(target_ip: *u8) -> i32
pub fn arp_handle_packet(arp_buf: *u8, len: u32)
```

### From main.ritz → net/ip.ritz

IPv4 layer (~150 lines):

```ritz
# net/ip.ritz
#
# Internet Protocol version 4 (Layer 3)

import net.types { IP_PROTO_ICMP, IP_PROTO_UDP, IP_PROTO_TCP }

pub const IP_HEADER_SIZE: u32 = 20

pub struct IpHeader
    version_ihl: u8
    tos: u8
    total_len: u16
    id: u16
    flags_frag: u16
    ttl: u8
    protocol: u8
    checksum: u16
    src_ip: [4]u8
    dst_ip: [4]u8

# Network configuration
var net_our_ip: [4]u8
var net_gateway: [4]u8
var net_netmask: [4]u8
var net_configured: u8 = 0

pub fn ip_init()
pub fn ip_set_config(ip: *u8, gateway: *u8, netmask: *u8)
pub fn ip_is_configured() -> bool
pub fn ip_get_our_ip() -> *u8
pub fn ip_get_gateway() -> *u8

pub fn ip_checksum(buf: *u8, len: u32) -> u16
pub fn ip_build_header(buf: *u8, dst_ip: *u8, protocol: u8, payload_len: u32) -> u32
```

### From main.ritz → net/icmp.ritz

ICMP protocol (~130 lines):

```ritz
# net/icmp.ritz
#
# Internet Control Message Protocol
# Handles ping (echo request/reply)

import net.types { ... }
import net.ip { ip_build_header, ip_checksum }
import net.eth { eth_build_frame }
import net.arp { arp_cache_lookup }

pub const ICMP_ECHO_REQUEST: u8 = 8
pub const ICMP_ECHO_REPLY: u8 = 0

pub struct IcmpEchoHeader
    type_code: u8
    code: u8
    checksum: u16
    id: u16
    seq: u16

var icmp_seq: u16 = 0
var icmp_waiting: u8 = 0

pub fn icmp_ping(dst_ip: *u8) -> i32
pub fn icmp_handle_packet(icmp_buf: *u8, len: u32, src_ip: *u8)
pub fn icmp_is_waiting() -> bool
```

### From main.ritz → net/udp.ritz

UDP protocol (~80 lines):

```ritz
# net/udp.ritz
#
# User Datagram Protocol (Layer 4)

import net.types { ... }

pub const UDP_HEADER_SIZE: u32 = 8

pub struct UdpHeader
    src_port: u16
    dst_port: u16
    length: u16
    checksum: u16

pub fn udp_build_header(buf: *u8, src_port: u16, dst_port: u16, payload_len: u32) -> u32
pub fn udp_handle_packet(udp_buf: *u8, len: u32, src_ip: *u8)
```

### From main.ritz → net/stack.ritz

Main network stack (~300 lines):

```ritz
# net/stack.ritz
#
# Network Stack - Main dispatch and coordination
#
# This is the central point that ties all layers together.
# Initializes the stack, polls for packets, dispatches to protocols.

import drivers.virtio.net { virtio_net_init, virtio_net_poll, virtio_net_send, virtio_net_get_mac }
import net.eth { eth_parse_header, EthHeader, ETH_HEADER_SIZE }
import net.arp { arp_init, arp_handle_packet }
import net.ip { ip_init, IpHeader, IP_HEADER_SIZE }
import net.icmp { icmp_handle_packet }
import net.udp { udp_handle_packet }
import net.types { ETHERTYPE_ARP, ETHERTYPE_IPV4, IP_PROTO_ICMP, IP_PROTO_UDP }

# RX buffer
var net_rx_buf: [2048]u8

pub fn net_stack_init() -> i32
    arp_init()
    ip_init()
    let result: i32 = virtio_net_init()
    if result < 0
        return result
    return 0

pub fn net_poll() -> i32
    let len: i32 = virtio_net_poll(@net_rx_buf[0], 2048)
    if len <= 0
        return 0

    # Parse Ethernet header
    var eth_hdr: EthHeader
    eth_parse_header(@net_rx_buf[0], @eth_hdr)

    let payload: *u8 = @net_rx_buf[0] + ETH_HEADER_SIZE as i64
    let payload_len: u32 = (len as u32) - ETH_HEADER_SIZE

    if eth_hdr.ethertype == ETHERTYPE_ARP
        arp_handle_packet(payload, payload_len)
        return 1

    if eth_hdr.ethertype == ETHERTYPE_IPV4
        # Parse IP, dispatch to ICMP/UDP/TCP
        ...

    return 0
```

### New: net/syscall.ritz

Network syscalls for userspace (~100 lines):

```ritz
# net/syscall.ritz
#
# Network syscalls exposed to Ring 3

import net.ip { ip_is_configured, ip_get_our_ip, ip_get_gateway }
import net.icmp { icmp_ping }
import drivers.virtio.net { virtio_net_get_mac }

pub const SYS_NET_INFO: i64 = 40
pub const SYS_NET_PING: i64 = 41

pub struct NetInfo
    configured: u8
    _padding: [3]u8
    ip: [4]u8
    gateway: [4]u8
    netmask: [4]u8
    mac: [6]u8
    _padding2: [2]u8

pub fn sys_net_info(info_ptr: *NetInfo) -> i64
    # Copy network config to userspace
    ...

pub fn sys_net_ping(ip_ptr: *u8, timeout_ms: i64) -> i64
    # Send ICMP echo, wait for reply
    ...
```

---

## Implementation Order

### Step 1: Create net/types.ritz
- Byte order functions
- Protocol constants
- Shared types

### Step 2: Create drivers/virtio/net.ritz
- Extract VirtIO-net driver from main.ritz
- Follow blk.ritz pattern exactly
- Test: driver init, MAC address read

### Step 3: Create net/eth.ritz
- Ethernet frame build/parse
- Test: can construct valid frames

### Step 4: Create net/arp.ritz
- ARP cache and protocol
- Test: ARP request/reply works

### Step 5: Create net/ip.ritz
- IP header construction
- Network config management
- Test: valid IP packets

### Step 6: Create net/icmp.ritz
- ICMP echo/reply
- Test: respond to incoming pings

### Step 7: Create net/udp.ritz
- UDP header construction
- Test: DHCP still works

### Step 8: Create net/stack.ritz
- Main init and poll loop
- Protocol dispatch
- Test: full stack integration

### Step 9: Create net/syscall.ritz
- sys_net_info
- sys_net_ping
- Test: userspace can query network

### Step 10: Update main.ritz
- Remove all extracted code
- Import net.stack
- Call net_stack_init() and net_poll()

### Step 11: Userspace utilities
- /bin/ping
- Shell ifconfig/ping commands

---

## Ring 1/2 Infrastructure (Future)

Once the stack is properly organized, we can split it:

### Ring 1: drivers/virtio/net.ritz
- Runs as privileged driver process
- Gets capabilities: IOPORT, IRQ, DMA memory
- Communicates with Ring 2 via IPC channel

### Ring 2: net/* (entire stack)
- Runs as system service (netd)
- Receives raw packets from Ring 1
- Exposes socket API to Ring 3

### Required kernel changes:
1. Process privilege levels (Ring 1, 2, 3)
2. TSS stack setup for Ring 1/2
3. Capability grants for I/O port access
4. IRQ delegation to Ring 1

This is **future work** - first we get the code organized properly in the kernel, then we can move it out.

---

## Testing Strategy

### Unit tests (per module):
- `net/types.ritz`: byte order conversions
- `net/eth.ritz`: frame construction
- `net/arp.ritz`: cache operations
- `net/ip.ritz`: checksum, header build

### Integration tests:
- DHCP obtains IP at boot
- Respond to incoming pings
- ARP resolution works

### End-to-end tests:
- `ping 10.0.2.2` (gateway) succeeds
- `ping 1.1.1.1` (external) succeeds
- Shell can run ping command

---

## Success Criteria

1. **Zero networking code in main.ritz** (except imports and calls)
2. **Each protocol in its own file** with clean interfaces
3. **VirtIO-net driver follows blk.ritz pattern**
4. **Userspace can ping external IPs**
5. **Code is ready for Ring 1/2 split** (no architectural debt)

---

## References

- `kernel/src/drivers/virtio/blk.ritz` - Pattern to follow
- `kernel/src/drivers/virtio/common.ritz` - Shared VirtIO code
- `kernel/src/main.ritz` lines 180-2100 - Code to extract
