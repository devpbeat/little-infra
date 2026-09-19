/**
 * Toggle between the mock adapter (fixture data, no backend required) and
 * a real HTTP client against the payments service.
 *
 * `VITE_USE_MOCK_API`:
 *   - "true"  -> always mock adapter
 *   - "false" -> always real HTTP client
 *   - unset (default) -> real API once authenticated (an API key is stored OR
 *     a staff session is established), mock otherwise, so the dashboard works
 *     standalone until someone logs in or pastes a key in Settings.
 */
const FORCED_MODE = import.meta.env.VITE_USE_MOCK_API;

const API_KEY_STORAGE_KEY = "payments-ui.api-key";

/**
 * Whether a staff session is active. `isUsingMockApi` is synchronous, but the
 * session check (`GET /auth/me`) is async, so `RequireAuth` records the outcome
 * here before the data queries fire. Reset on failed/absent session.
 */
let sessionAuthenticated = false;

export function setSessionAuthenticated(value: boolean): void {
  sessionAuthenticated = value;
}

export function getStoredApiKey(): string | null {
  try {
    return localStorage.getItem(API_KEY_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredApiKey(value: string | null): void {
  try {
    if (value) {
      localStorage.setItem(API_KEY_STORAGE_KEY, value);
    } else {
      localStorage.removeItem(API_KEY_STORAGE_KEY);
    }
  } catch {
    /* localStorage unavailable (e.g. private mode) — key just won't persist */
  }
}

export function isUsingMockApi(): boolean {
  if (FORCED_MODE === "true") return true;
  if (FORCED_MODE === "false") return false;
  return !getStoredApiKey() && !sessionAuthenticated;
}

/** Same-origin by default — the Vite dev server proxies `/api` to the payments backend. */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/** Absolute path to the Django admin, used by screens with no REST-managed CRUD. */
export const ADMIN_BASE_URL = import.meta.env.VITE_ADMIN_BASE_URL ?? "/admin/";
