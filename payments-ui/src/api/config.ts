/**
 * Toggle between the mock adapter (fixture data, no backend required) and
 * a real HTTP client against the payments service.
 *
 * `VITE_USE_MOCK_API`:
 *   - "true"  -> always mock adapter
 *   - "false" -> always real HTTP client
 *   - unset (default) -> real API once an API key is stored, mock otherwise,
 *     so the dashboard works standalone until someone pastes a key in
 *     Settings.
 */
const FORCED_MODE = import.meta.env.VITE_USE_MOCK_API;

const API_KEY_STORAGE_KEY = "payments-ui.api-key";

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
  return !getStoredApiKey();
}

/** Same-origin by default — the Vite dev server proxies `/api` to the payments backend. */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/** Absolute path to the Django admin, used by screens with no REST-managed CRUD. */
export const ADMIN_BASE_URL = import.meta.env.VITE_ADMIN_BASE_URL ?? "/admin/";
