import { useState } from "react";
import { getStoredApiKey, isUsingMockApi, setStoredApiKey } from "../../api/config";

/**
 * Stores the API key (`Authorization: Api-Key <prefix>.<secret>`) used by
 * the http client. Presence of a key switches the app out of mock mode
 * (see `api/config.ts::isUsingMockApi`).
 */
export function ApiKeyBar() {
  const [value, setValue] = useState(getStoredApiKey() ?? "");
  const [saved, setSaved] = useState(false);

  return (
    <div className="api-key-bar">
      <div className="stat-card-label">API key {isUsingMockApi() ? "(mock mode)" : "(live)"}</div>
      <div className="api-key-field">
        <input
          type="password"
          className="text-input"
          placeholder="prefix.secret"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setSaved(false);
          }}
        />
        <button
          className="btn btn-secondary"
          type="button"
          onClick={() => {
            setStoredApiKey(value || null);
            setSaved(true);
            window.location.reload();
          }}
        >
          Save
        </button>
      </div>
      {saved && <div style={{ fontSize: 11, color: "var(--text-dim)" }}>Saved.</div>}
    </div>
  );
}
