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

## Who runs this

Running the pipeline belongs to AGAST #1849, which owns the AWS account
check (`aws sts get-caller-identity`), the cost guard (t3.micro,
auto-destroy, 15-minute ceiling) and the stored serial log. CI and task-room
agents never run `terraform apply` or `terraform plan` against an AWS account.
The repo's tests (`projects/ritz/ritz0/test_indium_iac.py`) check these files
offline only.

## One guarded boot: `run.sh` and `boot-run/` (AGAST #1849)

`run.sh` (or `make -C projects/indium ec2-boot`) is the way to boot harland
on Nitro and keep the evidence:

1. checks `aws sts get-caller-identity` is account 412381736149, else exits 3;
2. `make ec2-disk`: rootless (`tools/mkec2disk.py`), with `init_interactive`
   so the instance ends at an rzsh prompt on the serial console;
3. uploads the image straight to an EBS snapshot with the EBS direct APIs
   (`tools/ebs_snapshot.py`): no builder instance;
4. `terraform apply` in `boot-run/`: an AMI, a no-ingress security group and
   one t3.micro (the only type `variables.tf` accepts; standard credits);
5. polls `aws ec2 get-console-output --latest` for `rzsh> ` (exit 0), and
   stops at once on `KERNEL PANIC` (exit 4);
6. saves the console to `projects/indium/boot-logs/<date>-<sha>.txt`
   (`--latest` returns the last 64 KiB of serial output);
7. from the EXIT trap, always: `aws ec2 terminate-instances`, then
   `terraform destroy`, checks `terraform state list` is empty (else exit 5,
   `LEAK`), deletes every snapshot tagged with the run's `RunId`, and prints
   the billed seconds and their cost.

Polling ends at most 840 s after apply began, so apply-to-termination stays
under the 15-minute ceiling. Billing stops at `shutting-down`, which is why
termination is requested before `terraform destroy`: a halted guest took
4m23s to finish terminating in the first live run.

`run.sh --dry-run` touches no AWS and is what the tests drive
(`projects/ritz/ritz0/test_indium_ec2_run.py`).

`boot-run/` keeps **local** state on purpose. The S3 state below
(`harland-ec2/terraform.tfstate`) still tracks a February 2026 deployment: a
running `harland-dev` t3.micro, a stopped builder, their volumes, an AMI and
two snapshots. A destroy against that state would delete resources a boot
run never created.

## The original pipeline: `deployment/`

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
