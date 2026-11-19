# One harland boot on Nitro: an AMI from the uploaded snapshot, a security
# group with no ingress, and one t3.micro. Nothing else: the serial console
# is read with `aws ec2 get-console-output --latest`, which needs no network
# path to the instance.

data "aws_vpc" "default" {
  default = true
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
  description = "Harland boot run: no inbound traffic"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_instance" "harland" {
  ami                         = aws_ami.harland.id
  instance_type               = var.instance_type
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
