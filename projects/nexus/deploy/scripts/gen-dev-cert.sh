#!/usr/bin/env bash
# gen-dev-cert.sh - generate the self-signed dev TLS cert for the nexus stack
#
# Writes deploy/certs/key.pem (EC P-256) and deploy/certs/cert.pem
# (CN=localhost, 365 days), which docker/docker-compose.yml mounts at /certs.
# Run it before `docker compose up`.  Existing files are kept unless
# --force is given.
#
# The pair is generated per checkout and never committed (*.pem is
# git-ignored): a private key in git is a published key (AGAST #1870).

set -euo pipefail

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../certs" && pwd)"
KEY="$CERT_DIR/key.pem"
CERT="$CERT_DIR/cert.pem"

if [[ "${1:-}" != "--force" && -s "$KEY" && -s "$CERT" ]]; then
    echo "dev cert already present: $CERT (use --force to regenerate)"
    exit 0
fi

umask 077
openssl req -x509 -nodes -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
    -keyout "$KEY" -out "$CERT" -days 365 -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null
# The container reads the key as a different uid; it is a throwaway dev key.
chmod 644 "$KEY" "$CERT"
echo "generated dev cert: $CERT"
