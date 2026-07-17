# contracts

Django admin app for managing contracts with independent clients. Author
Markdown contract templates, keep a list of clients/leads, then assign a
template to a client to auto-generate a document and push it to **DocuSeal**
for signature via its API. Signed PDFs are archived to **MinIO**.

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

## Setup

```bash
cd contracts
cp env.example .env          # deploy.sh does this too and prompts for blanks
# Fill: DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DJANGO_SUPERUSER_PASSWORD,
#       DOCUSEAL_API_TOKEN, DOCUSEAL_WEBHOOK_SECRET, OWNER_SIGNER_*
docker compose up -d --build
```

### One-time DocuSeal wiring

1. In DocuSeal (`sign.ignitesolutions.click`) → **Settings → API**: create a
   token → set `DOCUSEAL_API_TOKEN`.
2. In DocuSeal → **Settings → Webhooks**: add a webhook to
   `https://contracts.ignitesolutions.click/webhooks/docuseal/` for the
   `submission.completed` / `form.completed` events, and add a custom header
   `X-Docuseal-Secret` (or a `?secret=` query param) equal to
   `DOCUSEAL_WEBHOOK_SECRET`.

## Deploy

`contracts` is in the root `deploy.sh` `STACKS` array. CI: pushes touching
`contracts/**` build the image via `.github/workflows/contracts.yml`, which
triggers the `.woodpecker.yml` deploy that rebuilds + redeploys on the server.
