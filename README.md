# little-infra

Self-hosted infrastructure for `ignitesolutions.click` running on a single Ubuntu VPS with Docker (compose + Swarm) behind Traefik v3.

## Architecture

```
Internet → Cloudflare (DNS only) → Traefik v3 → Services
```

All services are on the `traefik_web` external network (compose) or `traefik_proxy` (Swarm stacks). Traefik handles TLS termination and routing based on `Host` labels.

### TLS Strategy

| Domain pattern | Resolver | Challenge |
|---|---|---|
| `*.ignitesolutions.click` | `myresolver` | HTTP-01 |
| `*.store.ignitesolutions.click` (wildcard) | `cloudflare` | DNS-01 via Cloudflare API |

Wildcard certs require `CF_DNS_API_TOKEN` in the Traefik container env. The Cloudflare record must be **DNS only** (gray cloud), not proxied.

---

## Stacks

| Directory | Description |
|---|---|
| `traefik/` | Reverse proxy, TLS, and Portainer |
| `ci/` | Woodpecker CI (pipeline runner) |
| `docuseal/` | Document signing (DocuSeal + Postgres) |
| `minio/` | S3-compatible object storage |
| `contracts/` | Django admin app for client contracts (DocuSeal + MinIO) |
| `homepage/` | Services dashboard |
| `k3s/` | Local WSL development stack (Helm-based) |

Other services (`n8n`, `ara`, `bugsink`, `aso-cjp`, etc.) live in their own repos and connect to the `traefik_web` / `traefik_proxy` network.

---

## Quick Start

### Prerequisites

- Docker + Docker Compose v2
- The `traefik_web` external network must exist:
  ```bash
  docker network create traefik_web
  docker network create traefik_proxy
  ```

### 1. Traefik

```bash
cd traefik

# Create the acme.json with correct permissions
touch acme.json && chmod 600 acme.json

# Copy and fill env vars
cp .env.example .env
# Required: CF_DNS_API_TOKEN (see below)

docker compose up -d
```

**Required env vars (`traefik/.env`):**

```env
CF_DNS_API_TOKEN=your_cloudflare_api_token
```

To generate a Cloudflare API token: Cloudflare Dashboard → My Profile → API Tokens → Create Token → use the "Edit zone DNS" template, scope it to `ignitesolutions.click`.

**Change the dashboard password:**
```bash
htpasswd -nb admin yournewpassword
# Paste the output into traefik/dynamic.yml under basicAuth.users
```

### 2. Woodpecker CI

```bash
cd ci

# Create a GitHub OAuth App:
# Settings → Developer settings → OAuth Apps → New OAuth App
# Homepage URL: https://ci.ignitesolutions.click
# Authorization callback URL: https://ci.ignitesolutions.click/authorize

# Fill in your .env:
cat > .env << 'EOF'
WOODPECKER_HOST=ci.ignitesolutions.click
WOODPECKER_GITHUB_CLIENT=<oauth_client_id>
WOODPECKER_GITHUB_SECRET=<oauth_client_secret>
WOODPECKER_AGENT_SECRET=$(openssl rand -hex 32)
WOODPECKER_ORGS=<your_github_org_or_username>
EOF

docker compose up -d
```

---

## Adding a New Service

Any compose service that should be reachable via Traefik needs:

1. Connected to the `traefik_web` network (or `traefik_proxy` for Swarm)
2. Labels declaring the router and TLS:

```yaml
services:
  myapp:
    image: myapp:latest
    networks:
      - web
    labels:
      - traefik.enable=true
      - traefik.http.routers.myapp.rule=Host(`myapp.ignitesolutions.click`)
      - traefik.http.routers.myapp.entrypoints=websecure
      - traefik.http.routers.myapp.tls=true
      - traefik.http.routers.myapp.tls.certresolver=myresolver
      - traefik.http.routers.myapp.middlewares=secure-headers@file
      - traefik.http.services.myapp.loadbalancer.server.port=3000

networks:
  web:
    external: true
    name: traefik_web
```

For wildcard subdomains (e.g. `*.store.ignitesolutions.click`), use `certresolver=cloudflare` and a `HostRegexp` rule:

```yaml
- traefik.http.routers.myapp.rule=HostRegexp(`^.+\.store\.ignitesolutions\.click$`)
- traefik.http.routers.myapp.tls.certresolver=cloudflare
- traefik.http.routers.myapp.tls.domains[0].main=store.ignitesolutions.click
- traefik.http.routers.myapp.tls.domains[0].sans=*.store.ignitesolutions.click
```

---

## CI/CD with Woodpecker

GitHub Actions handles build + test + image push (where applicable).
Woodpecker deploys on the server, running as a container on the same VPS as
every other stack (`ci/docker-compose.yml`), watching this same GitHub repo.

**Flow:**
```
push to main → GitHub Actions (build + push image to GHCR, if the service has one)
             → Woodpecker (native GitHub push event, same repo) → docker compose on the server
```

Woodpecker is activated directly on this GitHub repo (Woodpecker UI →
"Add repository"), so it receives the same `push` webhook GitHub already
sends for Actions — there is no separate curl-based deploy trigger step in
the workflows, and no `WOODPECKER_TOKEN`/`WOODPECKER_REPO`/
`WOODPECKER_DEPLOY_URL` secrets to manage. Each service's pipeline lives in
`.woodpecker/<service>.yml` (Woodpecker's multi-pipeline convention — one
file per deployable stack, each with its own `when.path` filter) instead of
a single root `.woodpecker.yml`. See:

- `.woodpecker/payments.yml` — payments API + payments-ui + Postgres,
  pulls images from GHCR (retries the pull since GitHub Actions' image push
  can still be in flight when Woodpecker's push event fires — same commit,
  two independent CI systems racing).
- `.woodpecker/contracts.yml` — builds the image locally on the server
  (no GHCR push exists for this service yet), no pull race.
- `.woodpecker/traefik.yml` — public images only, lighter retry, but
  restarts the shared edge proxy for every service on the box — review
  changes carefully.
- `.woodpecker/ci.yml` — redeploys Woodpecker itself; deliberately
  `event: manual` only (self-referential: it would be restarting its own
  agent mid-pipeline), triggered by hand from the Woodpecker UI.

**Host checkout path:** every pipeline step bind-mounts the server's actual
repo checkout at the *same* path inside the step container (assumed
`/home/ubuntu/little-infra` — adjust in each `.woodpecker/*.yml` if your server
uses a different path). This is required because `docker compose` runs
against the host's dockerd over the mounted `/var/run/docker.sock`, so any
relative paths it resolves (`env_file: .env`, build context, named
volumes) must exist at that exact path on the *host*, not in Woodpecker's
ephemeral git-clone workspace. It also means each service's real, gitignored
`.env` (already present on the server per `deploy.sh`'s `ensure_env`) is
used automatically — no secrets need to be duplicated into Woodpecker.

**Activating a repo in the Woodpecker UI (one-time, per pipeline you want
active):**
1. Log into `https://ci.ignitesolutions.click` with the GitHub account set
   as `WOODPECKER_ADMIN` (see `ci/env.example`).
2. "Add repository" → select this repo.
3. Repo settings → enable **Trusted** (or the "Trusted clone plugin" /
   volumes permission, depending on Woodpecker version) — required because
   these pipelines mount `/var/run/docker.sock` and a host path, which
   Woodpecker blocks for untrusted repos by default.
4. Repo settings → confirm the default branch is `main` and push events are
   enabled (on by default once trusted).
5. For `.woodpecker/ci.yml`, no toggle is needed beyond activation — it
   only runs when manually triggered from the pipeline list.

"Automatic deploy" now means: pushing to `main` with changes under a
service's watched paths redeploys that service's stack on the VPS, with no
manual curl/API call anywhere in the chain.

---

## Security Notes

- `traefik.yml` — static config only, no secrets
- `dynamic.yml` — middlewares; update `basicAuth.users` before deploying
- `acme.json` — must be `chmod 600`, never commit
- `CF_DNS_API_TOKEN` — scoped to DNS edit on `ignitesolutions.click` only
- All services use `no-new-privileges: true`
- HTTP is redirected to HTTPS globally (configured in `traefik.yml`)
- HSTS, X-Frame-Options, X-Content-Type-Options set via `secure-headers@file` middleware

---

## k3s (Local WSL Dev)

Helm-based stack for local development under WSL.

```bash
cd k3s
sh scripts/create-secrets.sh
helm upgrade --install infra helm/infra-stack -n infra --create-namespace -f values.yaml
```

See `k3s/README.md` for details.
