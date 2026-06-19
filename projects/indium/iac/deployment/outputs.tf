output "builder_instance_id" {
  description = "Builder instance ID"
  value       = aws_instance.builder.id
}

output "builder_public_ip" {
  description = "Builder public IP"
  value       = aws_instance.builder.public_ip
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "ebs_volume_id" {
  description = "Boot EBS volume ID"
  value       = aws_ebs_volume.harland.id
}

output "harland_instance_id" {
  description = "Harland instance ID"
  value       = aws_instance.harland.id
}

output "harland_public_ip" {
  description = "Harland public IP"
  value       = aws_instance.harland.public_ip
}

output "harland_ami_id" {
  description = "Generated Harland AMI ID"
  value       = aws_ami.harland.id
}

output "snapshot_id" {
  description = "Boot snapshot ID"
  value       = aws_ebs_snapshot.harland.id
}

output "ssh_builder_command" {
  description = "SSH command for builder"
  value       = "ssh -i ~/.ssh/id_ed25519 ubuntu@${aws_instance.builder.public_ip}"
}

output "get_console_output" {
  description = "Command to fetch latest Harland serial console output"
  value       = "aws ec2 get-console-output --instance-id ${aws_instance.harland.id} --region ${var.aws_region} --output text"
}
