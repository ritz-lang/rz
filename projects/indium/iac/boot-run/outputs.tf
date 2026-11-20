output "instance_id" {
  description = "The harland instance"
  value       = aws_instance.harland.id
}

output "ami_id" {
  description = "The AMI registered from the snapshot"
  value       = aws_ami.harland.id
}

# AGAST #1851: the acceptance peer, empty when peer_ping is false. Splat
# keeps the zero-count case from indexing an empty list.
output "peer_instance_id" {
  description = "The instance that pings harland, or empty"
  value       = join("", aws_instance.peer[*].id)
}

output "peer_ip" {
  description = "The peer's private IP (the source in harland's serial log), or empty"
  value       = join("", aws_instance.peer[*].private_ip)
}

output "harland_ip" {
  description = "Harland's private IP, what the peer pings"
  value       = aws_instance.harland.private_ip
}
