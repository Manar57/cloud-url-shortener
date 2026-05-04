output "public_ip" {
  value = aws_eip.app_ip.public_ip
}

# output "public_dns" {
#   value = aws_instance.app_server.public_dns
# }

output "public_dns" {
  value = data.aws_instance.current.public_dns
}