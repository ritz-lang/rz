# Boot logs from real hardware

Serial console captures of harland booting on EC2 Nitro, written by
`projects/indium/iac/run.sh` (AGAST #1849) as `<date>-<sha>.txt`. Each file
starts with a `#` header (commit, instance, capture time, result), followed by
`aws ec2 get-console-output --latest` verbatim: the last 64 KiB of serial
output, ANSI escapes included.

`2026-11-19-07405bc21b1e.txt`: the first Nitro boot (t3.micro, us-west-2).
UEFI, NVMe, ACPI/APIC, the AP, ENA, DHCP and gateway pings all work. Then the
kernel panics before init (#4334). The raw IPv4 bytes in the ring-buffer dump
near the end are part of that evidence, so the file is kept byte for byte and
git calls it binary.

`2026-11-20-d6937a69d5a3.txt`: the #1851 acceptance boot. It records the ENA
admin/IO setup, a VPC DHCP lease (`[dhcp] ACK: 172.31.8.135`), a peer
t3.micro in the same subnet pinging harland (`[icmp] Echo request from
172.31.1.18` then `[icmp] Sent reply to 172.31.1.18`), the totals
(`[net] peer ping: requests=1 replies=1`), and the 300-frame TX burst
(`sent=300/300 replies=244`). The `# --- peer console` section at the end is
the peer's own view: `PEER: got a ping reply from 172.31.8.135 after 0
tries`. Getting there needed three fixes recorded in that log's boot: the
I/O completion-queue head doorbell where the device names one, TX completion
reaping so a 256-slot ring is not overwritten (the first burst answered
244/300 before), and an ICMP reply to the received frame's L2 source with
buffers large enough for a standard 64-byte ping.

The header's `# commit:` names the tree that built the image. A later squash
rewrites that commit, so the `# image:` sha256 line — the bytes that actually
booted — is the durable identifier. Both console captures come from the same
run; the peer is gone once the run's trap terminates it.
