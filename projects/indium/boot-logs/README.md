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
