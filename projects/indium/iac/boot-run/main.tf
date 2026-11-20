# One harland boot on Nitro: an AMI from the uploaded snapshot, a security
# group that admits only the peer's ICMP, and one t3.micro. The serial
# console is read with `aws ec2 get-console-output --latest`, which needs no
# network path to the instance.
#
# AGAST #1851 adds the acceptance peer: a second t3.micro in the same subnet
# whose user-data pings harland's private IP until it gets a reply. Harland's
# serial log then shows the inbound echo request and the reply it sent.
# Nothing else is reachable.

data "aws_vpc" "default" {
  default = true
}

# Both instances must share a subnet for the peer's ping to be a direct
# ARP + ICMP exchange, so the subnet is chosen once and used by both.
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

locals {
  subnet_id = sort(data.aws_subnets.default.ids)[0]
}

resource "aws_ami" "harland" {
  name                = "harland-boot-run-${var.run_id}"
  description         = "Harland (indium) boot run ${var.run_id}, AGAST #1849"
  virtualization_type = "hvm"
  architecture        = "x86_64"
  boot_mode           = "uefi"
  ena_support         = true
  root_device_name    = "/dev/xvda"

  ebs_block_device {
    device_name           = "/dev/xvda"
    snapshot_id           = var.snapshot_id
    volume_type           = "gp3"
    delete_on_termination = true
  }
}

resource "aws_security_group" "harland" {
  name        = "harland-boot-run-${var.run_id}"
  description = "Harland boot run: peer ICMP only; egress for DHCP and pings"
  vpc_id      = data.aws_vpc.default.id

  # The acceptance peer pings harland; self = true covers both directions
  # because both instances join this one group. ICMP type/code -1 means all.
  ingress {
    description = "ICMP from the peer instance (AGAST #1851 acceptance)"
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    self        = true
  }

  # DHCP and the gateway ping are outbound; without this nothing is sent.
  egress {
    description = "DHCP, gateway and peer pings"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "harland" {
  ami                         = aws_ami.harland.id
  instance_type               = var.instance_type
  subnet_id                   = local.subnet_id
  vpc_security_group_ids      = [aws_security_group.harland.id]
  associate_public_ip_address = false

  # A guest that powers off ends the bill: terminate, not stop.
  instance_initiated_shutdown_behavior = "terminate"

  # t3 defaults to unlimited, which bills surplus CPU credits; a kernel
  # spinning at 100% for the whole run would earn some.
  credit_specification {
    cpu_credits = "standard"
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = {
    Name = "harland-boot-run-${var.run_id}"
  }
}

# A stock Amazon Linux 2023 image, only to run one ping loop. It is not the
# boot artefact under test.
data "aws_ami" "peer" {
  count       = var.peer_ping ? 1 : 0
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "peer" {
  count = var.peer_ping ? 1 : 0

  ami                         = data.aws_ami.peer[0].id
  instance_type               = var.instance_type
  subnet_id                   = local.subnet_id
  vpc_security_group_ids      = [aws_security_group.harland.id]
  associate_public_ip_address = false

  # The loop ends by powering off, and powering off ends the bill.
  instance_initiated_shutdown_behavior = "terminate"

  credit_specification {
    cpu_credits = "standard"
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  # Ping harland until it answers. Harland's responder window is 240 s and
  # this loop runs for 420 s, so the two overlap even when this instance's
  # boot (and cloud-init) is much slower. Progress, the gateway ping and the
  # last failed attempt go to the serial console, which run.sh captures next
  # to harland's log, so a peer that never runs is distinguishable from one
  # that never got a reply.
  user_data = <<-EOT
    #!/bin/sh
    target="${aws_instance.harland.private_ip}"
    echo "PEER: script start, target $target" > /dev/console
    gw=$(ip route | awk '/^default/ {print $3; exit}')
    echo "PEER: gateway $gw: $(ping -c 1 -W 1 "$gw" 2>&1 | tr '\n' ' ')" > /dev/console
    i=0
    while [ $i -lt 420 ]; do
      if out=$(ping -c 1 -W 1 "$target" 2>&1); then
        echo "PEER: got a ping reply from $target after $i tries: $(echo "$out" | head -1)" > /dev/console
        # Stay up briefly so run.sh captures this line from the peer console;
        # the run's EXIT trap terminates the instance regardless.
        sleep 60
        shutdown -h now
        exit 0
      fi
      i=$((i+1))
      if [ $((i % 30)) -eq 0 ]; then
        echo "PEER: $i tries to $target: $(echo "$out" | tail -1)" > /dev/console
      fi
      sleep 1
    done
    echo "PEER: no reply from $target after $i tries" > /dev/console
    shutdown -h now
  EOT

  tags = {
    Name = "harland-boot-run-peer-${var.run_id}"
  }
}
