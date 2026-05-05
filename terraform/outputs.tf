output "public_ip" {
  value = aws_eip.app_ip.public_ip
}