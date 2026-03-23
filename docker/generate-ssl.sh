#!/bin/bash
# Script to generate self-signed SSL certificates for development

# Create ssl directory if it doesn't exist
mkdir -p ssl

# Generate self-signed certificate (valid for 365 days)
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
  -subj "/C=ES/ST=Madrid/L=Madrid/O=42/CN=localhost"

echo "SSL certificates generated in docker/ssl/"
echo "cert.pem and key.pem created"
