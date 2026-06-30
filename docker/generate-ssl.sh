#!/bin/bash
# Generate a self-signed SSL certificate for local development.
#
# NOTE: In Docker the certificate is generated at runtime by the `ssl-init`
# service straight into the `ssl_certs` volume — nothing is committed to git.
# This script is only a manual/host fallback (e.g. running nginx outside Docker).
set -e

# Resolve the docker/ssl directory relative to this script, so it works from
# any CWD. Override with the first argument to target a different directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SSL_DIR="${1:-$SCRIPT_DIR/ssl}"

mkdir -p "$SSL_DIR"

if [ -f "$SSL_DIR/cert.pem" ] && [ -f "$SSL_DIR/key.pem" ]; then
  echo "SSL certificates already exist in $SSL_DIR — skipping."
  exit 0
fi

# Self-signed certificate, valid 365 days.
openssl req -x509 -newkey rsa:4096 -nodes -days 365 \
  -keyout "$SSL_DIR/key.pem" -out "$SSL_DIR/cert.pem" \
  -subj "/C=ES/ST=Madrid/L=Madrid/O=42/CN=localhost"

echo "SSL certificates generated in $SSL_DIR (cert.pem, key.pem)"
