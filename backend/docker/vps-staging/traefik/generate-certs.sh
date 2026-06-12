#!/bin/bash
# =============================================================================
# Generate self-signed TLS certificates for VPS-staging Traefik
# Output: certs/traefik-selfsigned.crt + certs/traefik-selfsigned.key
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/certs"
mkdir -p "${CERTS_DIR}"

CERT_FILE="${CERTS_DIR}/traefik-selfsigned.crt"
KEY_FILE="${CERTS_DIR}/traefik-selfsigned.key"

if [ -f "${CERT_FILE}" ] && [ -f "${KEY_FILE}" ]; then
  echo "✅ Self-signed certs already exist:"
  echo "   Cert: ${CERT_FILE}"
  echo "   Key:  ${KEY_FILE}"
  exit 0
fi

echo "🔐 Generating self-signed TLS certificate for VPS-staging Traefik..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "${KEY_FILE}" \
  -out "${CERT_FILE}" \
  -subj "/C=US/ST=State/L=City/O=LitInkAI/OU=VPS-Staging/CN=staging.litinkai.local" \
  -addext "subjectAltName=DNS:staging.litinkai.local,DNS:*.staging.litinkai.local"

chmod 600 "${KEY_FILE}"
chmod 644 "${CERT_FILE}"

echo "✅ Self-signed certs generated:"
echo "   Cert: ${CERT_FILE}"
echo "   Key:  ${KEY_FILE}"
echo ""
echo "   CN: staging.litinkai.local"
echo "   SAN: staging.litinkai.local, *.staging.litinkai.local"
echo "   Valid: 365 days"
