output "instance_id" {
  description = "The harland instance"
  value       = aws_instance.harland.id
}

output "ami_id" {
  description = "The AMI registered from the snapshot"
  value       = aws_ami.harland.id
}
