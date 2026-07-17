#!/bin/bash
set -e

STACKS=(traefik ci contracts)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

green() { echo -e "\033[32m$*\033[0m"; }
yellow() { echo -e "\033[33m$*\033[0m"; }
red() { echo -e "\033[31m$*\033[0m"; }

ensure_env() {
  local dir="$SCRIPT_DIR/$1"
  local example="$dir/env.example"
  local env="$dir/.env"

  [[ ! -f "$example" ]] && return 0

  if [[ ! -f "$env" ]]; then
    yellow "  No .env found for $1 — creating from env.example"
    cp "$example" "$env"
  fi

  local missing=0
  while IFS= read -r line <&3; do
    # Skip comments and blank lines
    [[ "$line" =~ ^# ]] && continue
    [[ -z "$line" ]] && continue

    local key="${line%%=*}"
    local current_val
    current_val=$(grep -E "^${key}=" "$env" | cut -d= -f2- || true)

    if [[ -z "$current_val" ]]; then
      missing=1
      read -rp "  Enter value for ${key}: " input </dev/tty
      # Escape special chars for sed
      local escaped
      escaped=$(printf '%s\n' "$input" | sed 's/[[\.*^$()+?{|]/\\&/g')
      sed -i "s|^${key}=.*|${key}=${escaped}|" "$env"
    fi
  done 3< "$example"

  if [[ "$missing" -eq 0 ]]; then
    green "  .env is complete"
  fi
}

deploy_stack() {
  local name="$1"
  local dir="$SCRIPT_DIR/$name"

  [[ ! -d "$dir" ]] && { yellow "  Skipping $name (directory not found)"; return; }
  [[ ! -f "$dir/docker-compose.yml" ]] && { yellow "  Skipping $name (no docker-compose.yml)"; return; }

  echo ""
  echo "==> $name"
  ensure_env "$name"

  (cd "$dir" && docker compose up -d --remove-orphans)
  green "  $name deployed"
}

echo ""
echo "little-infra deploy"
echo "==================="

for stack in "${STACKS[@]}"; do
  deploy_stack "$stack"
done

echo ""
green "Done."
