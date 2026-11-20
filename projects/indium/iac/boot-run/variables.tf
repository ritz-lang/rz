variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "run_id" {
  description = "Identifies one run.sh run; every resource and the snapshot carry it as the RunId tag"
  type        = string
}

variable "snapshot_id" {
  description = "EBS snapshot of build/ec2-boot.img, uploaded by tools/ebs_snapshot.py"
  type        = string
}

variable "instance_type" {
  description = "Instance type. Aaron's cost guard: t3.micro only"
  type        = string
  default     = "t3.micro"

  validation {
    condition     = var.instance_type == "t3.micro"
    error_message = "The cost guard allows t3.micro only (AGAST #1849); anything else goes to Aaron."
  }
}

variable "peer_ping" {
  description = "Launch the one ping peer for the #1851 acceptance (same t3.micro type, same subnet)"
  type        = bool
  default     = true
}
