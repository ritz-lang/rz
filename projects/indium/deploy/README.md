# Harland EC2 Deployment

Deploy the Harland microkernel (Indium distribution) to AWS EC2 as a custom UEFI-bootable AMI.

## Overview

This deployment uses a "builder pattern":
1. Boot an Ubuntu EC2 instance with an attached EBS volume
2. Copy the Harland disk image and `dd` it to the EBS volume
3. Create an AMI from the EBS snapshot
4. Boot a new instance from the custom AMI
5. View Harland output via AWS EC2 serial console

## Prerequisites

- **AWS CLI** configured with appropriate credentials
- **Terraform** >= 1.0
- **Build tools**: `sgdisk`, `mkfs.vfat`, losetup (for creating GPT disk images)
- **SSH key**: `~/.ssh/id_ed25519` (or configure `ssh_private_key_path`)

### Install dependencies (Ubuntu/Debian)

```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Disk image tools
sudo apt install gdisk dosfstools mtools
```

## Quick Start

```bash
cd projects/indium/deploy/scripts
./deploy.sh
```

This will:
1. Build the Harland kernel
2. Create an EC2-compatible disk image (GPT + ESP)
3. Initialize Terraform (creates S3 bucket for state)
4. Deploy to EC2
5. Wait for boot and display serial output

## Commands

```bash
./deploy.sh           # Full deployment
./deploy.sh build     # Just build the disk image
./deploy.sh init      # Initialize Terraform
./deploy.sh apply     # Apply Terraform (deploy)
./deploy.sh console   # Get serial console output
./deploy.sh status    # Show instance status
./deploy.sh destroy   # Tear down all resources
./deploy.sh help      # Show help
```

## Manual Steps

### Build disk image only

```bash
cd projects/indium
make ec2-disk
```

### Terraform only

```bash
cd projects/indium/deploy/terraform
terraform init
terraform plan
terraform apply
```

### View serial output

```bash
# Using deploy script
./scripts/deploy.sh console

# Or directly with AWS CLI
INSTANCE_ID=$(terraform -chdir=terraform output -raw harland_instance_id)
aws ec2 get-console-output --instance-id $INSTANCE_ID --region us-west-2 --output text | base64 -d
```

## Configuration

Edit `terraform/main.tf` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-west-2` | AWS region |
| `environment` | `dev` | Environment name (affects resource naming) |
| `ssh_public_key` | Aaron's key | SSH key for builder access |
| `ssh_private_key_path` | `~/.ssh/id_ed25519` | Private key for provisioning |
| `disk_image_path` | `../../build/ec2-boot.img` | Path to disk image |

### Using local Terraform state

Comment out the `backend "s3"` block in `main.tf`:

```hcl
# backend "s3" {
#   bucket  = "ritz-harland-terraform-state"
#   key     = "harland-ec2/terraform.tfstate"
#   region  = "us-west-2"
#   encrypt = true
# }
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Deployment Flow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Local Machine                                                  │
│  ┌─────────────────┐                                           │
│  │ make ec2-disk   │ ──► build/ec2-boot.img (GPT + ESP)       │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐     ┌─────────────────┐                  │
│  │ terraform apply │ ──► │ Ubuntu Builder  │                  │
│  └─────────────────┘     │   (t3.micro)    │                  │
│                          │     + EBS       │                  │
│                          └────────┬────────┘                  │
│                                   │                            │
│                          SCP + dd │ to /dev/nvme1n1            │
│                                   ▼                            │
│                          ┌─────────────────┐                  │
│                          │  EBS Snapshot   │                  │
│                          └────────┬────────┘                  │
│                                   │                            │
│                          Register │ AMI (boot_mode=uefi)       │
│                                   ▼                            │
│                          ┌─────────────────┐                  │
│                          │ Harland Instance│ ◄── Serial       │
│                          │   (t3.micro)    │     Console      │
│                          └─────────────────┘     Output       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Disk Image Format

The EC2-compatible disk image has:

```
┌────────────────────────────────────────────────┐
│ GPT Partition Table                            │
├────────────────────────────────────────────────┤
│ Partition 1: EFI System Partition (type EF00)  │
│   Filesystem: FAT32                            │
│   Contents:                                    │
│     /EFI/BOOT/BOOTX64.EFI  (UEFI bootloader)  │
│     /harland/kernel.elf    (Harland kernel)    │
│     /startup.nsh           (UEFI shell script) │
└────────────────────────────────────────────────┘
```

## Cost

All resources use free-tier eligible options:

| Resource | Cost |
|----------|------|
| t3.micro (builder + harland) | ~$0.01/hr each (free tier: 750 hrs/month) |
| gp3 EBS (1GB) | ~$0.08/month |
| EBS Snapshot (1GB) | ~$0.05/month |
| **Total** | ~$0.13/month + instance hours |

## Troubleshooting

### No console output

EC2 console output may take 1-2 minutes to appear after boot. Wait and retry:

```bash
./deploy.sh console
```

### UEFI boot fails

Verify the AMI has UEFI boot mode:

```bash
aws ec2 describe-images --image-ids $(terraform output -raw harland_ami_id) \
    --query 'Images[0].BootMode'
# Should output: "uefi"
```

### Builder SSH fails

Check that the builder instance is running:

```bash
./deploy.sh status
```

If the security group is correct but SSH times out, the instance may still be initializing. Wait for cloud-init to complete.

### EBS volume not appearing

On Nitro instances, `/dev/xvdf` appears as `/dev/nvme1n1`. The provisioner handles this automatically.

## Cleanup

```bash
./deploy.sh destroy
```

This removes:
- EC2 instances (builder + harland)
- EBS volume and snapshot
- AMI
- Security groups
- Key pair

The S3 bucket for Terraform state is NOT deleted (intentional).
