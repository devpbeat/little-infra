#!/usr/bin/env bash
# Generate contracts/.env from env.example.
#
# Auto-fills the secrets (Django key, Postgres password, superuser password,
# DocuSeal webhook secret) with random values and prompts for the handful of
# things only you know (DocuSeal API token, your signer name/email).
#
# Usage:  ./gen-env.sh          # interactive
#         ./gen-env.sh -y       # non-interactive: random secrets, leave prompts blank
set -euo pipefail

cd "$(dirname "$0")"

EXAMPLE=env.example
OUT=.env
ASSUME_YES=false
[[ "${1:-}" == "-y" || "${1:-}" == "--yes" ]] && ASSUME_YES=true

[[ -f "$EXAMPLE" ]] || { echo "error: $EXAMPLE not found (run from the contracts/ dir)" >&2; exit 1; }

if [[ -f "$OUT" && "$ASSUME_YES" == false ]]; then
  read -rp ".env already exists. Overwrite? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
fi

# A URL/shell-safe random secret of N bytes (base64, stripped of +/=).
rand() { openssl rand -base64 "${1:-36}" | tr -d '+/=' | cut -c1-"${2:-48}"; }

# Django needs the full symbol set; keep it single-quoted in the file.
DJANGO_SECRET_KEY=$(openssl rand -base64 60 | tr -d '\n')
POSTGRES_PASSWORD=$(rand 24 32)
DJANGO_SUPERUSER_PASSWORD=$(rand 18 24)
DOCUSEAL_WEBHOOK_SECRET=$(rand 24 32)

# Values only you know — prompt unless -y.
DOCUSEAL_API_TOKEN=""
OWNER_SIGNER_NAME=""
OWNER_SIGNER_EMAIL=""
if [[ "$ASSUME_YES" == false ]]; then
  echo "Fill these now (or leave blank and edit .env later):"
  read -rp "  DocuSeal API token (Settings -> API): " DOCUSEAL_API_TOKEN
  read -rp "  Your name  (Owner counter-signer):     " OWNER_SIGNER_NAME
  read -rp "  Your email (Owner counter-signer):     " OWNER_SIGNER_EMAIL
fi

# Copy env.example, substituting each blank KEY= with its value. Only fills
# keys that are empty in the example so pre-set defaults are preserved.
fill() { # fill KEY VALUE
  local key=$1 val=$2
  # escape & and | for sed replacement
  val=${val//\\/\\\\}; val=${val//&/\\&}; val=${val//|/\\|}
  sed -i "s|^${key}=$|${key}=${val}|" "$OUT"
}

cp "$EXAMPLE" "$OUT"
fill DJANGO_SECRET_KEY          "$DJANGO_SECRET_KEY"
fill POSTGRES_PASSWORD          "$POSTGRES_PASSWORD"
fill DJANGO_SUPERUSER_PASSWORD  "$DJANGO_SUPERUSER_PASSWORD"
fill DOCUSEAL_WEBHOOK_SECRET    "$DOCUSEAL_WEBHOOK_SECRET"
fill DOCUSEAL_API_TOKEN         "$DOCUSEAL_API_TOKEN"
fill OWNER_SIGNER_NAME          "$OWNER_SIGNER_NAME"
fill OWNER_SIGNER_EMAIL         "$OWNER_SIGNER_EMAIL"

chmod 600 "$OUT"

echo
echo "Wrote $OUT (chmod 600). Generated secrets:"
echo "  DJANGO_SUPERUSER_USERNAME = admin"
echo "  DJANGO_SUPERUSER_PASSWORD = $DJANGO_SUPERUSER_PASSWORD"
echo "  DOCUSEAL_WEBHOOK_SECRET   = $DOCUSEAL_WEBHOOK_SECRET   (set this on the DocuSeal webhook)"
[[ -z "$DOCUSEAL_API_TOKEN" ]] && echo "  ! DOCUSEAL_API_TOKEN is still blank — fill it before pushing contracts."
echo
echo "Next: docker compose up -d --build"
