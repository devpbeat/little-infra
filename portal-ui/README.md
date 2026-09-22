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

All routes are implemented as UI-only screens (see `src/App.tsx`):

- `/` — Landing / Marketplace (product list, hardcoded placeholder pricing)
- `/login` — Login / Sign up (UI only, no real auth yet)
- `/products/:slug` — Product detail (plans, demo credentials)
- `/dashboard` — Customer dashboard (subscribed apps, usage)
- `/admin/products` — Admin product management
- `/checkout` — Checkout (plan summary, payment form)

Authentication and payments are currently stubs (`console.log` + TODO
comments across the pages, e.g. `src/pages/LoginPage.tsx`,
`src/pages/CheckoutPage.tsx`, `src/pages/DashboardPage.tsx`). Real auth will
be **Clerk (Organizations)** and real billing will go through the existing
**Payments** service — both are wired in later slices. Do not add Clerk,
Stripe, or any auth/payments SDK before those slices are scoped.

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
