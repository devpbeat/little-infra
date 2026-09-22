#!/bin/sh
# ensure-env.sh <stack-dir>
#
# Non-interactive .env bootstrap for a stack, safe to run from CI/Woodpecker.
# Seeds <dir>/.env from <dir>/env.example:
#   - creates .env from env.example when it does not exist
#   - for every key declared in env.example that is empty/missing in .env,
#     fills it from a same-named environment variable when one is set,
#     otherwise from the example's own (default) value
#   - exits non-zero, listing the keys, if any required value is still empty
#
# It never prompts and never overwrites an existing non-empty value, so it is
# idempotent: running it on an already-complete .env is a no-op. For the
# interactive local workflow use deploy.sh's ensure_env instead.
#
# Usage:
#   sh scripts/ensure-env.sh portal
#   PLATFORM_NETWORK=platform sh scripts/ensure-env.sh portal   # inject a secret
set -eu

dir="${1:?usage: ensure-env.sh <stack-dir>}"
example="$dir/env.example"
env_file="$dir/.env"

if [ ! -f "$example" ]; then
  echo "ensure-env: no env.example in $dir — nothing to do"
  exit 0
fi

if [ ! -f "$env_file" ]; then
  echo "ensure-env: creating $env_file from env.example"
  cp "$example" "$env_file"
fi

missing=""

# Iterate the keys declared in env.example (skip comments and blank lines).
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    ''|\#*) continue ;;
  esac
  key="${line%%=*}"
  [ "$key" = "$line" ] && continue   # not a KEY=value line

  # Already set to a non-empty value in .env? leave it untouched.
  current="$(grep -E "^${key}=" "$env_file" 2>/dev/null | tail -n1 | cut -d= -f2- || true)"
  [ -n "$current" ] && continue

  # Prefer a same-named environment variable (lets CI inject secrets),
  # then fall back to the example's own default value.
  eval "injected=\${$key:-}"
  if [ -n "${injected:-}" ]; then
    val="$injected"
  else
    val="$(grep -E "^${key}=" "$example" | tail -n1 | cut -d= -f2- || true)"
  fi

  if [ -z "$val" ]; then
    missing="$missing $key"
    continue
  fi

  # Escape for a sed replacement using | as the delimiter.
  esc="$(printf '%s' "$val" | sed 's/[&|\\]/\\&/g')"
  if grep -qE "^${key}=" "$env_file"; then
    tmp="$(mktemp)"
    sed "s|^${key}=.*|${key}=${esc}|" "$env_file" > "$tmp" && mv "$tmp" "$env_file"
  else
    printf '%s=%s\n' "$key" "$val" >> "$env_file"
  fi
done < "$example"

if [ -n "$missing" ]; then
  echo "ensure-env: missing required value(s) for:$missing" >&2
  echo "ensure-env: set them as environment variables or fill $env_file by hand" >&2
  exit 1
fi

echo "ensure-env: $env_file is complete"
