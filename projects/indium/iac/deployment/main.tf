data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_vpc" "default" {
  default = true
}

locals {
  name_prefix = "harland"
}

resource "aws_key_pair" "deployer" {
  key_name   = "${local.name_prefix}-deployer-${var.environment}"
  public_key = var.ssh_public_key != "" ? var.ssh_public_key : file(pathexpand(var.ssh_public_key_path))
}

resource "aws_security_group" "builder" {
  name        = "${local.name_prefix}-builder-${var.environment}"
  description = "Security group for Harland AMI builder"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_ingress_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-builder-${var.environment}"
  }
}

resource "aws_security_group" "harland" {
  name        = "${local.name_prefix}-${var.environment}"
  description = "Security group for Harland OS instance"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-${var.environment}"
  }
}

resource "aws_instance" "builder" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.builder_instance_type
  subnet_id              = var.subnet_id
  key_name               = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.builder.id]
  availability_zone      = var.availability_zone

  instance_initiated_shutdown_behavior = "stop"

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = {
    Name = "${local.name_prefix}-builder-${var.environment}"
  }
}

resource "aws_ebs_volume" "harland" {
  availability_zone = var.availability_zone
  size              = var.boot_volume_size_gb
  type              = "gp3"
  iops              = 3000
  throughput        = 125

  tags = {
    Name = "${local.name_prefix}-os-${var.environment}"
  }
}

resource "aws_ebs_volume" "initramfs" {
  availability_zone = var.availability_zone
  size              = var.initramfs_volume_size_gb
  type              = "gp3"
  iops              = 3000
  throughput        = 125

  tags = {
    Name = "${local.name_prefix}-initramfs-${var.environment}"
  }
}

resource "aws_volume_attachment" "harland_to_builder" {
  device_name = "/dev/xvdf"
  volume_id   = aws_ebs_volume.harland.id
  instance_id = aws_instance.builder.id
}

resource "aws_volume_attachment" "initramfs_to_builder" {
  device_name = "/dev/xvdg"
  volume_id   = aws_ebs_volume.initramfs.id
  instance_id = aws_instance.builder.id
}

resource "null_resource" "enable_serial_console" {
  provisioner "local-exec" {
    command = "aws ec2 enable-serial-console-access --region ${var.aws_region} || true"
  }
}

resource "null_resource" "burn_image" {
  depends_on = [
    aws_volume_attachment.harland_to_builder,
    aws_volume_attachment.initramfs_to_builder,
  ]

  triggers = {
    disk_image_hash  = var.disk_image_hash
    initramfs_hash   = var.initramfs_hash
    boot_volume_id   = aws_ebs_volume.harland.id
    initramfs_volume = aws_ebs_volume.initramfs.id
  }

  provisioner "local-exec" {
    command = <<-EOT
      if [ "${var.enable_burn_steps}" != "true" ]; then
        echo "burn disabled (set -var='enable_burn_steps=true' to run)"
        exit 0
      fi
      scp -i ${pathexpand(var.builder_ssh_private_key_path)} -o StrictHostKeyChecking=no ${var.disk_image_path} ${var.initramfs_image_path} ${var.builder_ssh_user}@${aws_instance.builder.public_ip}:/tmp/
      ssh -i ${pathexpand(var.builder_ssh_private_key_path)} -o StrictHostKeyChecking=no ${var.builder_ssh_user}@${aws_instance.builder.public_ip} \
        "sudo dd if=/tmp/$(basename ${var.disk_image_path}) of=/dev/nvme1n1 bs=4M conv=fsync status=progress && \
         sudo dd if=/tmp/$(basename ${var.initramfs_image_path}) of=/dev/nvme2n1 bs=4M conv=fsync status=progress && \
         sync"
    EOT
  }
}

resource "null_resource" "detach_volume" {
  depends_on = [null_resource.burn_image]

  triggers = {
    always_run = var.detach_trigger_id
  }

  provisioner "local-exec" {
    command = <<-EOT
      if [ "${var.enable_burn_steps}" != "true" ]; then
        echo "detach disabled (set -var='enable_burn_steps=true' to run)"
        exit 0
      fi
      aws ec2 detach-volume --region ${var.aws_region} --volume-id ${aws_ebs_volume.harland.id} || true
      aws ec2 detach-volume --region ${var.aws_region} --volume-id ${aws_ebs_volume.initramfs.id} || true
    EOT
  }
}

resource "null_resource" "stop_builder" {
  depends_on = [null_resource.detach_volume]

  triggers = {
    always_run = var.stop_trigger_id
  }

  provisioner "local-exec" {
    command = <<-EOT
      if [ "${var.enable_burn_steps}" != "true" ]; then
        echo "stop disabled (set -var='enable_burn_steps=true' to run)"
        exit 0
      fi
      aws ec2 stop-instances --region ${var.aws_region} --instance-ids ${aws_instance.builder.id}
      aws ec2 wait instance-stopped --region ${var.aws_region} --instance-ids ${aws_instance.builder.id}
    EOT
  }
}

resource "aws_ebs_snapshot" "harland" {
  depends_on = [null_resource.stop_builder]

  volume_id   = aws_ebs_volume.harland.id
  description = var.boot_snapshot_description

  tags = {
    Name = "${local.name_prefix}-boot-snapshot-${var.environment}"
  }

  timeouts {
    create = "30m"
  }
}

resource "aws_ebs_snapshot" "initramfs" {
  depends_on = [null_resource.stop_builder]

  volume_id   = aws_ebs_volume.initramfs.id
  description = var.initramfs_snapshot_description

  tags = {
    Name = "${local.name_prefix}-initramfs-snapshot-${var.environment}"
  }

  timeouts {
    create = "30m"
  }
}

resource "aws_ami" "harland" {
  name                = var.harland_ami_name
  description         = "Harland Microkernel (Indium Distribution)"
  virtualization_type = "hvm"
  architecture        = "x86_64"
  root_device_name    = "/dev/xvda"
  boot_mode           = "uefi"
  ena_support         = true

  ebs_block_device {
    device_name           = "/dev/xvda"
    snapshot_id           = aws_ebs_snapshot.harland.id
    volume_size           = var.boot_volume_size_gb
    volume_type           = "gp3"
    delete_on_termination = true
  }

  ebs_block_device {
    device_name           = "/dev/xvdb"
    snapshot_id           = aws_ebs_snapshot.initramfs.id
    volume_size           = var.initramfs_volume_size_gb
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = {
    Name = "${local.name_prefix}-${var.environment}"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_instance" "harland" {
  ami                    = aws_ami.harland.id
  instance_type          = var.harland_instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.harland.id]
  availability_zone      = var.availability_zone

  instance_initiated_shutdown_behavior = "stop"

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  ebs_block_device {
    device_name           = "/dev/xvdb"
    snapshot_id           = aws_ebs_snapshot.initramfs.id
    volume_size           = var.initramfs_volume_size_gb
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = {
    Name = "${local.name_prefix}-${var.environment}"
  }
}
