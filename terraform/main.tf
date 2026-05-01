provider "aws" {
  region = var.region
}

resource "aws_instance" "app" {
  ami           = "ami-08c40ec9ead489470"  # Amazon Linux 2 (Free Tier)
  instance_type = var.instance_type

  user_data = file("setup.sh")

  tags = {
    Name = "url-shortener"
  }
}