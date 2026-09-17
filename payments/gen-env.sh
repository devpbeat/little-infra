#!/usr/bin/env bash
# Generate payments/.env from env.example.
#
# Auto-fills the secrets (Django key, Postgres password, superuser password,
# webhook path token) with random values and prompts for the handful of
# things only you know (Pagopar keys, Anthropic API key).
#
# Usage:  ./gen-env.sh          # interactive
#         ./gen-env.sh -y       # non-interactive: random secrets, leave prompts blank
set -euo pipefail

cd "$(dirname "$0")"

EXAMPLE=env.example
OUT=.env
ASSUME_YES=false
[[ "${1:-}" == "-y" || "${1:-}" == "--yes" ]] && ASSUME_YES=true

[[ -f "$EXAMPLE" ]] || { echo "error: $EXAMPLE not found (run from the payments/ dir)" >&2; exit 1; }

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
WEBHOOK_PATH_TOKEN=$(rand 24 32)

# Values only you know — prompt unless -y. Pagopar private key is read
# silently (it is a credential, keep it out of terminal scrollback).
PAGOPAR_PUBLIC_KEY=""
PAGOPAR_PRIVATE_KEY=""
ANTHROPIC_API_KEY=""
if [[ "$ASSUME_YES" == false ]]; then
  echo "Fill these now (or leave blank and edit .env later):"
  read -rp  "  Pagopar public key:                  " PAGOPAR_PUBLIC_KEY
  read -rsp "  Pagopar private key (hidden input):  " PAGOPAR_PRIVATE_KEY; echo
  read -rsp "  Anthropic API key (hidden, optional): " ANTHROPIC_API_KEY; echo
fi

# Copy env.example, substituting each blank KEY= with its value. Only fills
# keys that are empty in the example so pre-set defaults are preserved.
fill() { # fill KEY VALUE
  local key=$1 val=$2
  val=${val//\\/\\\\}; val=${val//&/\\&}; val=${val//|/\\|}
  sed -i "s|^${key}=$|${key}=${val}|" "$OUT"
}

cp "$EXAMPLE" "$OUT"
fill DJANGO_SECRET_KEY         "$DJANGO_SECRET_KEY"
fill POSTGRES_USER             "payments"
fill POSTGRES_PASSWORD         "$POSTGRES_PASSWORD"
fill DJANGO_SUPERUSER_USERNAME "admin"
fill DJANGO_SUPERUSER_EMAIL    "admin@ignitesolutions.click"
fill DJANGO_SUPERUSER_PASSWORD "$DJANGO_SUPERUSER_PASSWORD"
fill WEBHOOK_PATH_TOKEN        "$WEBHOOK_PATH_TOKEN"
fill PAGOPAR_PUBLIC_KEY        "$PAGOPAR_PUBLIC_KEY"
fill PAGOPAR_PRIVATE_KEY       "$PAGOPAR_PRIVATE_KEY"
fill ANTHROPIC_API_KEY         "$ANTHROPIC_API_KEY"

chmod 600 "$OUT"

echo
echo "Wrote $OUT (chmod 600). Generated secrets:"
echo "  DJANGO_SUPERUSER_USERNAME = admin"
echo "  DJANGO_SUPERUSER_PASSWORD = $DJANGO_SUPERUSER_PASSWORD"
[[ -z "$PAGOPAR_PRIVATE_KEY" ]] && echo "  ! PAGOPAR_PRIVATE_KEY is blank — webhooks will reject EVERYTHING until it is set (fail-closed)."
[[ -z "$ANTHROPIC_API_KEY" ]] && echo "  ! ANTHROPIC_API_KEY is blank — contract template generation stays disabled until it is set."
echo
echo "Next: docker compose pull && docker compose up -d"
