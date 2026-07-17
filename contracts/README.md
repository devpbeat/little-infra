# contracts

Django admin app for managing contracts with independent clients. Author
Markdown contract templates, keep a list of clients/leads, then assign a
template to a client to auto-generate a document and push it to **DocuSeal**
for signature via its API. Signed PDFs are archived to **MinIO**.

The admin is themed with [django-unfold](https://unfoldadmin.com/) — a modern
sidebar, light/dark toggle, and coloured status badges for clients and contracts.

- URL: `https://contracts.ignitesolutions.click`
- Depends on the already-running `docuseal` and `minio` stacks (reached over
  the shared `traefik_web` network at `http://docuseal:3000` / `http://minio:9000`).

## How it works

1. **Templates** (`ContractTemplate`) — Markdown edited in the admin with a
   live-preview editor. Two placeholder syntaxes:
   - `${merge_var}` — filled in by this app before sending. Client fields are
     always available (`${client_name}`, `${client_email}`, `${client_company}`,
     `${client_address}`, `${client_tax_id}`, `${client_phone}`) plus any keys
     from a contract's `variables` JSON (e.g. `${amount}`, `${start_date}`).
   - `{{Signature;role=Client;type=signature}}` — a DocuSeal interactive field,
     left untouched for the signer to complete in DocuSeal. Use
     `role=Owner` for your counter-signature.
2. **Clients** (`Client`) — leads with a sales status.
3. **Contracts** (`Contract`) — pick a client + template, fill `variables`, then
   run the **"Generate & push to DocuSeal"** admin action. The app renders the
   Markdown to HTML, creates a DocuSeal submission (Client + Owner submitters,
   `send_email=false`), and stores each signer's public signing link.
4. **Completion** — a DocuSeal webhook to `/webhooks/docuseal/` downloads the
   signed PDF and archives it in the MinIO `contracts` bucket (auto-created).

## Deploy

The `docuseal` and `minio` stacks must already be up (they share the
`traefik_web` network this app reaches them over).

```bash
cd contracts
./gen-env.sh                 # generate .env: random secrets + a few prompts
docker compose up -d --build
```

`gen-env.sh` copies `env.example` → `.env`, auto-fills the secrets
(`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `DJANGO_SUPERUSER_PASSWORD`,
`DOCUSEAL_WEBHOOK_SECRET`) with random values, and prompts for the three things
only you know (`DOCUSEAL_API_TOKEN`, `OWNER_SIGNER_NAME`, `OWNER_SIGNER_EMAIL`).
Run `./gen-env.sh -y` to skip the prompts (leaves those blank to edit later).
It prints the generated superuser password and webhook secret — note them down.

On first boot `entrypoint.sh` runs migrations, `collectstatic`, and creates the
`DJANGO_SUPERUSER_*` admin user (idempotent). The app then serves on `:8000`
behind Traefik at `https://contracts.ignitesolutions.click` — log into
`/admin` with the superuser. The MinIO `contracts` bucket is auto-created on
first archive.

### One-time DocuSeal wiring

1. In DocuSeal (`sign.ignitesolutions.click`) → **Settings → API**: create a
   token → put it in `.env` as `DOCUSEAL_API_TOKEN`, then
   `docker compose up -d` again to pick it up.
2. In DocuSeal → **Settings → Webhooks**: add a webhook to
   `https://contracts.ignitesolutions.click/webhooks/docuseal/` for the
   `submission.completed` / `form.completed` events, and add a custom header
   `X-Docuseal-Secret` (or a `?secret=` query param) equal to your
   `DOCUSEAL_WEBHOOK_SECRET`.

### Environment reference

All config is env-driven (`env.example` is the source of truth). Highlights:

| Var | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django crypto key — keep secret, unique per deploy |
| `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` | Add your host here if you change the domain |
| `POSTGRES_*` | Bundled `contracts-postgres` credentials |
| `DOCUSEAL_URL` / `DOCUSEAL_PUBLIC_URL` | Internal API endpoint / public host used to build signing links |
| `DOCUSEAL_API_TOKEN` / `DOCUSEAL_WEBHOOK_SECRET` | API auth / shared webhook secret |
| `OWNER_SIGNER_NAME` / `OWNER_SIGNER_EMAIL` | You, added as the `Owner` counter-signer on every contract |
| `MINIO_ENDPOINT` / `MINIO_PUBLIC_ENDPOINT` | Internal S3 endpoint / public host for presigned download links |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` / `MINIO_BUCKET` | MinIO credentials + archive bucket |

### Ops

```bash
docker compose logs -f contracts          # app logs
docker compose exec contracts python manage.py createsuperuser   # extra admin
docker compose exec contracts python manage.py migrate           # after code updates
docker compose up -d --build              # redeploy after pulling changes
```

## CI / automated deploy

`contracts` is in the root `deploy.sh` `STACKS` array. CI: pushes touching
`contracts/**` build the image via `.github/workflows/contracts.yml`, which
triggers the `.woodpecker.yml` deploy that rebuilds + redeploys on the server.
