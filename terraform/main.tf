terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_security_group" "app_sg" {
  name        = "url-shortener-sg"
  description = "Allow HTTP and SSH"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 5001
    to_port     = 5001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "app_server" {
  ami           = "ami-0c02fb55956c7d316" # Amazon Linux
  instance_type = "t3.micro"

  security_groups = [aws_security_group.app_sg.name]

      user_data = <<-EOF
              #!/bin/bash
              yum update -y
              yum install -y docker git
              systemctl start docker
              systemctl enable docker
              usermod -aG docker ec2-user
              mkdir -p /home/ec2-user/.ssh
              echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDJlOIqF+l/uiRDVwaYcqjn7VnS1vw7R/HvjnrGFfYnBB8pxlsQm+6A7fH2ny1Dp8bXeJrKi5lM7TivAmZYbE/cYRlVzgq3306TR+Ldmv1oQAxnCbSajCM1wyjY+iSAQVVI6GmS9e/P3BdRzGgsAIgHOKgx7sPusNiSqImfQ8dENP4XZ7hOqLS8PTBBc0iEcQyp+YRWX4iXGc/fnA6bek/nXwHxhDWzSTDrv3tRoBaAHlQ1NS5853jdMzYTHntcaWkyRFjUFNrfE8drhgwRyLEA/F0inDWaW0aBeC/lFYgeR7SZuw6I3xnsBls1+jM9OnmahRFwKZnBnTYOdYvyuJ1wk82C1Rz4JOCx5CblpiJ3CucbFE7PFCzDs5vo89+5FOgaASya5xO7yH7g13SiZH1z2QcH6PwGQE93olSbPbLt2DsYwcguP6u0TjCCqXlv/vEDe+Kclri0IVN0rQkEpB1yY62RV/wuuYGhpjfU4F2/lYe6uKWRMQur/f8zzgB7ODtgIiIOKqyvb52r0ZTVCRZy1rY8ddjKC6ww0YL0PscENpf3y1v+U7Is1f9m3DTysJtRFWSbwKAKLjedwG51s0iPgWMR2wz74Xd1PuqL/sIYoUybJxvj4VayEQK/IKfXX/2gZdludYsthcB9r8kZjkvpl1IMAopRWVhWFyQvDLNVbw== manar@زينب-05049" >> /home/ec2-user/.ssh/authorized_keys
              chown -R ec2-user:ec2-user /home/ec2-user/.ssh
              chmod 700 /home/ec2-user/.ssh
              chmod 600 /home/ec2-user/.ssh/authorized_keys

              mkdir -p /usr/local/lib/docker/cli-plugins
              curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
              chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

              cd /home/ec2-user
              git clone https://github.com/Manar57/cloud-url-shortener.git
              cd cloud-url-shortener
              docker compose up -d --build
              EOF

  tags = {
    Name = "url-shortener-server"
  }
}

resource "aws_eip" "app_ip" {
  domain = "vpc"
}

resource "aws_eip_association" "app_ip_assoc" {
  instance_id   = aws_instance.app_server.id
  allocation_id = aws_eip.app_ip.id
}
