#!/bin/bash
yum update -y
yum install docker -y
service docker start
usermod -a -G docker ec2-user

curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

git clone https://github.com/Manar57/cloud-url-shortener.git
cd cloud-url-shortener

docker-compose up -d