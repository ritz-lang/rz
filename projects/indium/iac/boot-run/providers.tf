# Local state on purpose (AGAST #1849). The S3 key harland-ec2/terraform.tfstate
# belongs to ../deployment and still tracks a February deployment; a destroy
# against it would delete resources this run never created. run.sh keeps this
# state in boot-run/ and checks that `terraform state list` is empty after
# every run.
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "harland-boot-run"
      RunId     = var.run_id
      ManagedBy = "terraform"
      Task      = "AGAST-1849"
    }
  }
}
