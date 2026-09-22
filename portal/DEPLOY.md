# Portal — Deploy Guide

Deploy guide for `portal/`: the `portal-ui` static site, routed at
`portal.ignitesolutions.click`. Mirrors the `payments`/`payments-ui`
convention (see `payments/DEPLOY.md`) but simpler — `portal-ui` is fully
static (no backend API to proxy to yet, no database, no migrations).

## 1. Prerequisites on the server

- `platform` stack already deployed (`platform/docker-compose.yml`) — this
  is where the shared `platform` Docker network lives, that Traefik uses to
  route to this stack's service.
- `traefik` stack already deployed and routing `*.ignitesolutions.click`
  with the `myresolver` cert resolver.
- DNS: `portal.ignitesolutions.click` must resolve to the VPS before first
  deploy, or the `myresolver` ACME HTTP-01 challenge will fail.

## 2. Environment

`deploy.sh` auto-creates `portal/.env` from `portal/env.example` on first
run. To prepare it manually instead:

```bash
cp portal/env.example portal/.env
chmod 600 portal/.env
```

Only two values: `PLATFORM_NETWORK` (must match `platform/.env`) and
`PORTAL_UI_TAG` (set by CI, defaults to `latest`).

## 3. First deploy

```bash
./deploy.sh
```

`portal` is included in `deploy.sh`'s `STACKS` array — no per-stack
migration step is needed (unlike `payments`), since `portal-ui` has no
database.

## 4. Woodpecker deploy trigger

Implemented in `.woodpecker/portal.yml`, mirroring `.woodpecker/payments.yml`:

1. `.github/workflows/portal-ui-ci.yml` builds+pushes
   `ghcr.io/devpbeat/portal-ui:<tag>` on push to `main`, gated on the
   `portal-ui/**` path filter and on lint+build passing first, then
   triggers the Woodpecker pipeline via the same curl-to-API pattern as
   `payments-ui-ci.yml`.
2. `.woodpecker/portal.yml` bind-mounts the server's checkout and the
   Docker socket, retries `docker compose pull` (tolerating the GHCR
   push/Woodpecker-trigger race), then `docker compose up -d
   --remove-orphans`. No migration step — there is nothing to migrate.

## 5. Rollback

Single static-asset service, no schema. Rollback is: `docker pull` the
previous tag, `docker compose up -d` with `PORTAL_UI_TAG=<previous-sha>` in
`.env`.

## 6. Known gaps (review before declaring live)

- No backend yet: the marketplace product list and pricing are hardcoded
  in `portal-ui/src/data/products.ts`, and login/signup are UI-only stubs
  (see `portal-ui/README.md`). Nothing here talks to a real API.
- `nginx.conf` has no reverse-proxy `location` block (unlike
  `payments-ui/nginx.conf`) — add one once portal-ui needs to reach a
  backend service (product/plan API, Clerk-backed auth, etc.).
