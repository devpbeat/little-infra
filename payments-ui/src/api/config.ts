/**
 * Toggle between the mock adapter (fixture data, no backend required) and
 * a real HTTP client against the payments service.
 *
 * Controlled via `VITE_USE_MOCK_API`:
 *   - unset or "true"  -> mock adapter (default; safe standalone mode)
 *   - "false"          -> real HTTP client against VITE_API_BASE_URL
 *
 * Defaults to mock mode because, as of this writing, `payments/` only
 * exposes a health check endpoint — the domain API is not live yet.
 */
export const USE_MOCK_API =
  (import.meta.env.VITE_USE_MOCK_API ?? "true") !== "false";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
