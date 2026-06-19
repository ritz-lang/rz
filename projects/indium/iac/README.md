# Indium IaC (Harland EC2)

Terraform configuration for the Harland EC2 deployment pipeline:

1. Launch builder instance (`aws_instance.builder`)
2. Attach burn volumes (`aws_ebs_volume.harland`, `aws_ebs_volume.initramfs`)
3. Burn images from local artifacts via SSH (`null_resource.burn_image`)
4. Snapshot burned volumes (`aws_ebs_snapshot.*`)
5. Register UEFI AMI (`aws_ami.harland`)
6. Launch Harland instance (`aws_instance.harland`)

The concrete entrypoint is `iac/deployment/` and uses the shared backend:

- Bucket: `ritz-harland-terraform-state`
- Key: `harland-ec2/terraform.tfstate`
- Region: `us-west-2`

## Usage

```bash
cd projects/indium/iac/deployment
terraform init
terraform plan
```

To enable burn/detach/stop steps during `apply`, set:

```bash
terraform apply -var='enable_burn_steps=true'
```

By default those lifecycle shell steps are disabled for safety and drift checks.
