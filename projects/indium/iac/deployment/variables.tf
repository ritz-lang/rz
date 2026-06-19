variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "availability_zone" {
  description = "AZ for builder and burn volumes"
  type        = string
  default     = "us-west-2a"
}

variable "subnet_id" {
  description = "Subnet ID for EC2 instances"
  type        = string
  default     = "subnet-0d676c6b66e7acb5b"
}

variable "builder_instance_type" {
  description = "Instance type for the AMI builder"
  type        = string
  default     = "t3.micro"
}

variable "harland_instance_type" {
  description = "Instance type for Harland runtime instance"
  type        = string
  default     = "t3.micro"
}

variable "boot_volume_size_gb" {
  description = "Size of boot volume in GiB"
  type        = number
  default     = 1
}

variable "initramfs_volume_size_gb" {
  description = "Size of initramfs volume in GiB"
  type        = number
  default     = 1
}

variable "ssh_public_key" {
  description = "SSH public key material for builder keypair"
  type        = string
  default     = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIE705J9TIPSzMqwLaEdYWfZ/E9eaY29TL35BuO5cBdMn aaron@huburght"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key if ssh_public_key is empty"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "builder_ssh_private_key_path" {
  description = "Private key path for SSH into builder"
  type        = string
  default     = "~/.ssh/id_ed25519"
}

variable "builder_ssh_user" {
  description = "Builder SSH user"
  type        = string
  default     = "ubuntu"
}

variable "ssh_ingress_cidrs" {
  description = "CIDRs allowed to SSH to builder"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "disk_image_path" {
  description = "Path to built EC2 boot image"
  type        = string
  default     = "../../build/ec2-boot.img"
}

variable "disk_image_hash" {
  description = "Pinned hash for EC2 boot image trigger"
  type        = string
  default     = "4c365c65997ae13d8e9a35d2fa1c206e"
}

variable "initramfs_image_path" {
  description = "Path to built initramfs image"
  type        = string
  default     = "../../build/initramfs.img"
}

variable "initramfs_hash" {
  description = "Pinned hash for initramfs image trigger"
  type        = string
  default     = "aca2735ae0f2fc26d9fbb91a37239cd4"
}

variable "detach_trigger_id" {
  description = "Pinned detach trigger from recovered state"
  type        = string
  default     = "2026-02-19T00:38:20Z"
}

variable "stop_trigger_id" {
  description = "Pinned stop trigger from recovered state"
  type        = string
  default     = "2026-02-19T00:37:32Z"
}

variable "boot_snapshot_description" {
  description = "Description for boot snapshot"
  type        = string
  default     = "Harland OS boot volume - 5510123137438000331"
}

variable "initramfs_snapshot_description" {
  description = "Description for initramfs snapshot"
  type        = string
  default     = "Harland initramfs volume - 5510123137438000331"
}

variable "harland_ami_name" {
  description = "AMI name for Harland deployment"
  type        = string
  default     = "harland-dev-20260219-004000"
}

variable "enable_burn_steps" {
  description = "Run destructive burn/detach/stop shell steps"
  type        = bool
  default     = false
}
