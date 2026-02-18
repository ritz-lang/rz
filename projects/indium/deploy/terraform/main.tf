# Harland EC2 Deployment
#
# Deploys the Harland microkernel (Indium distribution) to AWS EC2 as a
# custom UEFI-bootable AMI.
#
# Workflow:
# 1. Boot Ubuntu builder instance with attached EBS volume
# 2. SCP disk image to builder, dd it to EBS volume
# 3. Stop builder, snapshot EBS, register UEFI AMI
# 4. Boot Harland instance from custom AMI
# 5. View output via `aws ec2 get-console-output`
#
# Usage:
#   cd projects/indium/deploy/terraform
#   terraform init
#   terraform apply
#
# Then check serial output:
#   terraform output -raw get_console_output | sh

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Comment this out for local-only state
  backend "s3" {
    bucket  = "ritz-harland-terraform-state"
    key     = "harland-ec2/terraform.tfstate"
    region  = "us-west-2"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "harland-ec2"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "ssh_public_key" {
  description = "SSH public key for builder access"
  type        = string
  default     = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIE705J9TIPSzMqwLaEdYWfZ/E9eaY29TL35BuO5cBdMn aaron@huburght"
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key for provisioning"
  type        = string
  default     = "~/.ssh/id_ed25519"
}

variable "disk_image_path" {
  description = "Path to the Harland UEFI boot disk image"
  type        = string
  default     = "../../build/ec2-boot.img"
}

variable "initramfs_path" {
  description = "Path to the initramfs TAR archive"
  type        = string
  default     = "../../build/initramfs.tar"
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------

# Get latest Ubuntu 24.04 AMI for builder
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Get default VPC
data "aws_vpc" "default" {
  default = true
}

# Get availability zones
data "aws_availability_zones" "available" {
  state = "available"
}

# -----------------------------------------------------------------------------
# Security Groups
# -----------------------------------------------------------------------------

# Security group for builder instance (SSH for provisioning)
resource "aws_security_group" "builder" {
  name        = "harland-builder-${var.environment}"
  description = "Security group for Harland AMI builder"
  vpc_id      = data.aws_vpc.default.id

  # SSH access for provisioning
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "harland-builder-${var.environment}"
  }
}

# Security group for Harland instance (minimal - serial console is via AWS API)
resource "aws_security_group" "harland" {
  name        = "harland-${var.environment}"
  description = "Security group for Harland OS instance"
  vpc_id      = data.aws_vpc.default.id

  # No ingress needed - Harland doesn't have a network stack yet
  # Serial console access is via AWS API, not network

  # Allow all outbound (for DHCP, etc. when networking is implemented)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "harland-${var.environment}"
  }
}

# -----------------------------------------------------------------------------
# SSH Key Pair
# -----------------------------------------------------------------------------

resource "aws_key_pair" "deployer" {
  key_name   = "harland-deployer-${var.environment}"
  public_key = var.ssh_public_key
}

# -----------------------------------------------------------------------------
# Builder Instance and EBS Volume
# -----------------------------------------------------------------------------

# Empty EBS volume that will contain the Harland OS boot partition
resource "aws_ebs_volume" "harland" {
  availability_zone = data.aws_availability_zones.available.names[0]
  size              = 1  # GB - minimal, just need ESP
  type              = "gp3"

  tags = {
    Name = "harland-os-${var.environment}"
  }
}

# EBS volume for initramfs (userspace programs + filesystem)
resource "aws_ebs_volume" "initramfs" {
  availability_zone = data.aws_availability_zones.available.names[0]
  size              = 1  # GB - TAR archive is small
  type              = "gp3"

  tags = {
    Name = "harland-initramfs-${var.environment}"
  }
}

# Ubuntu builder instance
resource "aws_instance" "builder" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t3.micro"
  key_name                    = aws_key_pair.deployer.key_name
  vpc_security_group_ids      = [aws_security_group.builder.id]
  availability_zone           = data.aws_availability_zones.available.names[0]
  associate_public_ip_address = true

  root_block_device {
    volume_size           = 8
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = {
    Name = "harland-builder-${var.environment}"
  }
}

# Attach the Harland boot EBS volume to builder
resource "aws_volume_attachment" "harland_to_builder" {
  device_name = "/dev/xvdf"
  volume_id   = aws_ebs_volume.harland.id
  instance_id = aws_instance.builder.id
}

# Attach the initramfs EBS volume to builder
resource "aws_volume_attachment" "initramfs_to_builder" {
  device_name = "/dev/xvdg"
  volume_id   = aws_ebs_volume.initramfs.id
  instance_id = aws_instance.builder.id
}

# -----------------------------------------------------------------------------
# Provisioning: Build and Burn Image
# -----------------------------------------------------------------------------

# Wait for builder to be ready and burn both images
resource "null_resource" "burn_image" {
  depends_on = [
    aws_volume_attachment.harland_to_builder,
    aws_volume_attachment.initramfs_to_builder
  ]

  # Re-run if disk image or initramfs changes
  triggers = {
    disk_image_hash  = filemd5(var.disk_image_path)
    initramfs_hash   = filemd5(var.initramfs_path)
    boot_volume_id   = aws_ebs_volume.harland.id
    initramfs_volume = aws_ebs_volume.initramfs.id
  }

  connection {
    type        = "ssh"
    user        = "ubuntu"
    host        = aws_instance.builder.public_ip
    private_key = file(pathexpand(var.ssh_private_key_path))
    timeout     = "5m"
  }

  # Wait for cloud-init and both EBS volumes
  provisioner "remote-exec" {
    inline = [
      "echo 'Waiting for cloud-init...'",
      "cloud-init status --wait",
      "echo 'Waiting for EBS volumes to appear...'",
      "while [ ! -e /dev/nvme1n1 ]; do sleep 1; done",
      "while [ ! -e /dev/nvme2n1 ]; do sleep 1; done",
      "echo 'EBS volumes ready at /dev/nvme1n1 and /dev/nvme2n1'"
    ]
  }

  # Copy both disk images
  provisioner "file" {
    source      = var.disk_image_path
    destination = "/tmp/harland-boot.img"
  }

  provisioner "file" {
    source      = var.initramfs_path
    destination = "/tmp/initramfs.tar"
  }

  # Burn both images to EBS volumes
  provisioner "remote-exec" {
    inline = [
      "echo 'Burning boot image to EBS volume (nvme1n1)...'",
      "sudo dd if=/tmp/harland-boot.img of=/dev/nvme1n1 bs=4M status=progress",
      "echo 'Burning initramfs to EBS volume (nvme2n1)...'",
      "sudo dd if=/tmp/initramfs.tar of=/dev/nvme2n1 bs=4M status=progress",
      "sudo sync",
      "rm /tmp/harland-boot.img /tmp/initramfs.tar",
      "echo 'Both images burned successfully!'"
    ]
  }
}

# Stop builder instance before creating snapshot
resource "null_resource" "stop_builder" {
  depends_on = [null_resource.burn_image]

  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOF
      echo "Stopping builder instance..."
      aws ec2 stop-instances --instance-ids ${aws_instance.builder.id} --region ${var.aws_region}
      echo "Waiting for instance to stop..."
      aws ec2 wait instance-stopped --instance-ids ${aws_instance.builder.id} --region ${var.aws_region}
      echo "Builder instance stopped."
    EOF
  }
}

# Detach both volumes from builder after stop
resource "null_resource" "detach_volume" {
  depends_on = [null_resource.stop_builder]

  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOF
      echo "Detaching EBS volumes..."
      aws ec2 detach-volume --volume-id ${aws_ebs_volume.harland.id} --region ${var.aws_region} || true
      aws ec2 detach-volume --volume-id ${aws_ebs_volume.initramfs.id} --region ${var.aws_region} || true
      echo "Waiting for volumes to be available..."
      aws ec2 wait volume-available --volume-ids ${aws_ebs_volume.harland.id} --region ${var.aws_region}
      aws ec2 wait volume-available --volume-ids ${aws_ebs_volume.initramfs.id} --region ${var.aws_region}
      echo "Both volumes detached and available."
    EOF
  }
}

# -----------------------------------------------------------------------------
# AMI Creation
# -----------------------------------------------------------------------------

# Create snapshot from the boot EBS volume
resource "aws_ebs_snapshot" "harland" {
  volume_id   = aws_ebs_volume.harland.id
  description = "Harland OS boot volume - ${null_resource.burn_image.id}"

  depends_on = [null_resource.detach_volume]

  tags = {
    Name = "harland-boot-snapshot-${var.environment}"
  }

  timeouts {
    create = "30m"
  }

  lifecycle {
    replace_triggered_by = [null_resource.burn_image.id]
  }
}

# Create snapshot from the initramfs EBS volume
resource "aws_ebs_snapshot" "initramfs" {
  volume_id   = aws_ebs_volume.initramfs.id
  description = "Harland initramfs volume - ${null_resource.burn_image.id}"

  depends_on = [null_resource.detach_volume]

  tags = {
    Name = "harland-initramfs-snapshot-${var.environment}"
  }

  timeouts {
    create = "30m"
  }

  lifecycle {
    replace_triggered_by = [null_resource.burn_image.id]
  }
}

# Register AMI from snapshots with UEFI boot mode
# Includes both boot volume (ESP) and data volume (initramfs)
resource "aws_ami" "harland" {
  name                = "harland-${var.environment}-${formatdate("YYYYMMDD-hhmmss", timestamp())}"
  description         = "Harland Microkernel (Indium Distribution)"
  architecture        = "x86_64"
  virtualization_type = "hvm"
  root_device_name    = "/dev/xvda"

  # CRITICAL: Set UEFI boot mode for Nitro instances
  boot_mode = "uefi"

  # CRITICAL: Enable ENA for Nitro instances (t3, etc.)
  ena_support = true

  # Boot volume (ESP with kernel + bootloader)
  ebs_block_device {
    device_name           = "/dev/xvda"
    snapshot_id           = aws_ebs_snapshot.harland.id
    volume_type           = "gp3"
    volume_size           = 1
    delete_on_termination = true
  }

  # Initramfs volume (raw TAR archive)
  # This will appear as /dev/nvme1n1 (second NVMe device) on Nitro instances
  ebs_block_device {
    device_name           = "/dev/xvdb"
    snapshot_id           = aws_ebs_snapshot.initramfs.id
    volume_type           = "gp3"
    volume_size           = 1
    delete_on_termination = true
  }

  depends_on = [aws_ebs_snapshot.harland, aws_ebs_snapshot.initramfs]

  tags = {
    Name = "harland-${var.environment}"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# -----------------------------------------------------------------------------
# Serial Console Setup
# -----------------------------------------------------------------------------

# Enable serial console access for the region (one-time setup)
resource "null_resource" "enable_serial_console" {
  provisioner "local-exec" {
    command = "aws ec2 enable-serial-console-access --region ${var.aws_region} || true"
  }
}

# -----------------------------------------------------------------------------
# Harland Instance
# -----------------------------------------------------------------------------

# Boot Harland from custom AMI
resource "aws_instance" "harland" {
  ami                    = aws_ami.harland.id
  instance_type          = "t3.micro"  # Nitro instance required for serial console + UEFI
  vpc_security_group_ids = [aws_security_group.harland.id]
  availability_zone      = data.aws_availability_zones.available.names[0]

  # Serial console requires IMDSv2
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  depends_on = [null_resource.enable_serial_console]

  tags = {
    Name = "harland-${var.environment}"
  }
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "builder_instance_id" {
  description = "Builder EC2 instance ID"
  value       = aws_instance.builder.id
}

output "builder_public_ip" {
  description = "Builder public IP (for debugging)"
  value       = aws_instance.builder.public_ip
}

output "harland_instance_id" {
  description = "Harland EC2 instance ID"
  value       = aws_instance.harland.id
}

output "harland_ami_id" {
  description = "Harland AMI ID"
  value       = aws_ami.harland.id
}

output "ebs_volume_id" {
  description = "Harland EBS volume ID"
  value       = aws_ebs_volume.harland.id
}

output "snapshot_id" {
  description = "Harland EBS snapshot ID"
  value       = aws_ebs_snapshot.harland.id
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "get_console_output" {
  description = "Command to get console output (boot log)"
  value       = "aws ec2 get-console-output --instance-id ${aws_instance.harland.id} --region ${var.aws_region} --output text"
}

output "ssh_builder_command" {
  description = "SSH command to connect to builder (when running)"
  value       = "ssh -i ${var.ssh_private_key_path} ubuntu@${aws_instance.builder.public_ip}"
}
