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

Authentication is now wired to **Clerk**, using Clerk Organizations as
tenants. Payments remain a stub (`console.log` + TODO comments, e.g.
`src/pages/CheckoutPage.tsx`) — real billing goes through the existing
**Payments** service (Pagopar backend remains the source of truth; no
Clerk Billing is used). Do not add Stripe or any payments SDK before that
slice is scoped.

## Authentication (Clerk)

Package: [`@clerk/react`](https://clerk.com/docs/references/react/overview)
(the current supported React SDK — `@clerk/clerk-react` is deprecated).
One Clerk instance is shared across the platform; each Clerk **Organization**
represents a customer tenant.

### Required env var

```
VITE_CLERK_PUBLISHABLE_KEY=pk_...
```

Get this from the Clerk dashboard → **API Keys** (the *publishable* key —
safe for the frontend/browser). The Clerk **secret** key is never needed by
this SPA and must not be set here.

The key is read at **runtime** (`src/main.tsx`), not build time: `npm run
build` succeeds without it, but the app throws a clear error at startup in
any environment missing it, so a misconfigured deploy fails loudly.

### Enabling Organizations + Google OAuth in the Clerk dashboard

1. Clerk dashboard → **Organizations** → enable Organizations for this
   application instance.
2. Clerk dashboard → **User & Authentication** → **Social Connections** →
   enable **Google**. (Already enabled for this project — nothing to do in
   code; Clerk's `<SignIn/>`/`<SignUp/>` components pick it up
   automatically.)

### Routes

- `/login` and `/signup` render Clerk's prebuilt `<SignIn/>` / `<SignUp/>`
  components (path-based routing, themed via the `appearance` prop in
  `src/lib/clerkAppearance.ts` to match the portal's orange `#FF5A1F` /
  Plus Jakarta Sans / pill-button design system). Both routes are mounted
  as `/login/*` and `/signup/*` in `src/App.tsx` — the catch-all is required
  by Clerk's path-based routing for its internal sub-steps (email
  verification, SSO callback, etc.).
- `/dashboard` and `/checkout` require an authenticated session
  (`RequireAuth` in `src/components/auth/RouteGuards.tsx`, built on Clerk's
  `<Show when="signed-in">`). Signed-out visitors are redirected to
  `/login`.
- `/admin/products` additionally requires **staff** access
  (`RequireStaff` in the same file).

### Granting staff access (`/admin/products`)

Staff gating uses `user.publicMetadata.staff === true` — chosen over an
org-role check because staff is a platform-level concept, not scoped to any
one tenant/organization. To grant it:

1. Clerk dashboard → **Users** → select the user → **Metadata** tab.
2. Under **Public metadata**, add:
   ```json
   { "staff": true }
   ```
3. Save. The user now passes `RequireStaff` on next sign-in/session refresh.

Non-staff users (and signed-out visitors) hitting `/admin/products` are
redirected to `/dashboard`.

### Dashboard identity

`DashboardPage` reads the real signed-in user via `useUser()` (first name,
avatar image or initials fallback) and renders Clerk's
`<OrganizationSwitcher/>` so the active tenant/organization is always
visible.

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
