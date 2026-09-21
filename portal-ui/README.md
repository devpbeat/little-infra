# portal-ui

Customer-facing control panel for Ignite Solutions, served at
`portal.ignitesolutions.click`. It is the single UI for all self-hosted
product subscriptions (DocuSeal, Payments, Ara, n8n Automations) — unlike
`payments`, which is backend-only.

`portal-ui` is a **fork of `payments-ui`**: same stack (React 19 + Vite 8 +
TypeScript + react-router-dom 7 + @tanstack/react-query + oxlint, served via
nginx) and the same conventions (plain CSS per component, `components/ui`
primitives, `src/pages` route components). It does not share code with
`payments-ui` — each fork evolves independently after the initial copy.

## Current slice

Only two routes exist so far:

- `/` — Landing / Marketplace (product list, hardcoded placeholder pricing)
- `/login` — Login / Sign up (UI only, no real auth yet)

Pricing, dashboard, admin, and checkout are out of scope for this slice.

Authentication is currently a stub (`console.log` + TODO comments in
`src/pages/LoginPage.tsx`). Real auth will be **Clerk (Organizations)**,
wired in a later slice — do not add Clerk or any auth SDK before that slice
is scoped.

## Dev commands

```bash
npm install
npm run dev       # http://localhost:5173
npm run lint      # oxlint
npm run build     # tsc -b && vite build
npm run preview   # preview the production build
```

## Deployment

Built and served the same way as `payments-ui`: a multi-stage Docker build
(Node build → nginx runtime), routed by Traefik. See `../portal/DEPLOY.md`
for the full deploy guide and `../portal/docker-compose.yml` for the
service definition. CI/CD mirrors `payments-ui`'s pipeline — see
`.github/workflows/portal-ui-ci.yml` (build/push to GHCR) and
`.woodpecker/portal.yml` (deploy trigger).
