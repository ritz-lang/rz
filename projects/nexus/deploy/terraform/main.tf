# Nexus Wiki - AWS Infrastructure
#
# Deploys a minimal EC2 instance running the full Ritz stack:
# - Mausoleum (document database)
# - Nexus (wiki application with embedded Valet HTTP server)
#
# Usage:
#   cd deploy/terraform
#   terraform init
#   terraform apply
#
# Then run the deploy script:
#   ../scripts/deploy.sh

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "ritz-nexus-terraform-state"
    key     = "nexus/terraform.tfstate"
    region  = "us-west-2"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "nexus"
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
  default     = "production"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"  # Cheapest x86, $0.0104/hr (~$7.50/month)
}

variable "ssh_public_key" {
  description = "SSH public key for access"
  type        = string
  default     = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIE705J9TIPSzMqwLaEdYWfZ/E9eaY29TL35BuO5cBdMn aaron@huburght"
}

variable "domain_name" {
  description = "Domain name for the wiki"
  type        = string
  default     = "ritz-lang.org"
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------

# Get latest Ubuntu 22.04 AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
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
# S3 Bucket for Terraform State (create separately if needed)
# -----------------------------------------------------------------------------

# Note: Run `terraform init` without backend first, then:
#   aws s3 mb s3://ritz-nexus-terraform-state --region us-west-2
#   aws s3api put-bucket-versioning --bucket ritz-nexus-terraform-state --versioning-configuration Status=Enabled
# Then uncomment backend and run `terraform init` again

# -----------------------------------------------------------------------------
# Security Group
# -----------------------------------------------------------------------------

resource "aws_security_group" "nexus" {
  name        = "nexus-${var.environment}"
  description = "Security group for Nexus wiki server"
  vpc_id      = data.aws_vpc.default.id

  # SSH access
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP access (Valet/Nexus)
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS access (future)
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
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
    Name = "nexus-${var.environment}"
  }
}

# -----------------------------------------------------------------------------
# SSH Key Pair
# -----------------------------------------------------------------------------

resource "aws_key_pair" "deployer" {
  key_name   = "nexus-deployer-${var.environment}"
  public_key = var.ssh_public_key
}

# -----------------------------------------------------------------------------
# EC2 Instance
# -----------------------------------------------------------------------------

resource "aws_instance" "nexus" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.nexus.id]

  # Use first available AZ
  availability_zone = data.aws_availability_zones.available.names[0]

  # Root volume
  root_block_device {
    volume_size           = 8  # GB, minimum for Ubuntu
    volume_type           = "gp3"
    delete_on_termination = true
    encrypted             = true
  }

  # User data to set up the instance
  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Update system
    apt-get update
    apt-get upgrade -y

    # Create ritz user and directories
    useradd -r -s /bin/false ritz || true
    mkdir -p /opt/ritz/bin
    mkdir -p /var/lib/mausoleum
    mkdir -p /var/log/ritz
    chown -R ritz:ritz /var/lib/mausoleum /var/log/ritz

    # Enable lingering for ritz user (allows user services without login)
    loginctl enable-linger ritz || true

    # Install useful tools
    apt-get install -y htop curl

    echo "Nexus server initialized" > /var/log/ritz/init.log
  EOF

  tags = {
    Name = "nexus-${var.environment}"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# -----------------------------------------------------------------------------
# Elastic IP (optional, for stable IP)
# -----------------------------------------------------------------------------

resource "aws_eip" "nexus" {
  instance = aws_instance.nexus.id
  domain   = "vpc"

  tags = {
    Name = "nexus-${var.environment}"
  }
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.nexus.id
}

output "public_ip" {
  description = "Public IP address (Elastic IP)"
  value       = aws_eip.nexus.public_ip
}

output "public_dns" {
  description = "Public DNS name"
  value       = aws_eip.nexus.public_dns
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = "ssh ubuntu@${aws_eip.nexus.public_ip}"
}

output "wiki_url" {
  description = "URL to access the wiki"
  value       = "http://${aws_eip.nexus.public_ip}/"
}

# -----------------------------------------------------------------------------
# Route53 - Domain Configuration
# -----------------------------------------------------------------------------

# Hosted zone for ritz-lang.org
resource "aws_route53_zone" "main" {
  name    = var.domain_name
  comment = "Ritz programming language ecosystem"

  tags = {
    Name = var.domain_name
  }
}

# A record - root domain points to EC2
resource "aws_route53_record" "root" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [aws_eip.nexus.public_ip]
}

# A record - www subdomain points to EC2
resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"
  ttl     = 300
  records = [aws_eip.nexus.public_ip]
}

# -----------------------------------------------------------------------------
# Route53 Outputs
# -----------------------------------------------------------------------------

output "domain_name" {
  description = "Domain name"
  value       = var.domain_name
}

output "nameservers" {
  description = "Nameservers to configure at your domain registrar"
  value       = aws_route53_zone.main.name_servers
}

output "domain_url" {
  description = "URL using domain name"
  value       = "http://${var.domain_name}/"
}
