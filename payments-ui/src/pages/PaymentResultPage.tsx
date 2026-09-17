import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Card } from "../components/ui";
import { API_BASE_URL } from "../api/config";

type ResultStatus = "pending" | "confirmed" | "failed" | "expired" | "unknown";

const POLL_INTERVAL_MS = 3000;
const POLL_MAX_ATTEMPTS = 20;

/**
 * Public landing page for Pagopar's post-checkout redirect
 * (`/payments/result/:hash`). Polls the equally public, status-only
 * backend endpoint — no login or API key required.
 */
export function PaymentResultPage() {
  const { hash } = useParams<{ hash: string }>();
  const [status, setStatus] = useState<ResultStatus>("pending");
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    if (!hash || status === "confirmed" || status === "failed" || status === "expired") return;
    if (attempts >= POLL_MAX_ATTEMPTS) return;
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/payments/result/${encodeURIComponent(hash)}`);
        if (res.ok) {
          const data = (await res.json()) as { status: ResultStatus };
          setStatus(data.status ?? "unknown");
        } else if (res.status === 404) {
          setStatus("unknown");
        }
      } catch {
        // Network hiccup: keep polling until attempts run out.
      }
      setAttempts((n) => n + 1);
    }, attempts === 0 ? 0 : POLL_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [hash, status, attempts]);

  return (
    <div style={{ maxWidth: 420, margin: "10vh auto", textAlign: "center" }}>
      <Card>
        {status === "confirmed" && (
          <>
            <div style={{ fontSize: 48 }}>✅</div>
            <h2 style={{ color: "var(--success, #4ade80)" }}>Payment accepted</h2>
            <p>Your subscription is active. You can close this window.</p>
          </>
        )}
        {(status === "failed" || status === "expired") && (
          <>
            <div style={{ fontSize: 48 }}>❌</div>
            <h2 style={{ color: "var(--danger, #f87171)" }}>
              {status === "expired" ? "Payment expired" : "Payment failed"}
            </h2>
            <p>The payment was not completed. Please try again from your invoice.</p>
          </>
        )}
        {status === "pending" && attempts < POLL_MAX_ATTEMPTS && (
          <>
            <div style={{ fontSize: 48 }}>⏳</div>
            <h2>Waiting for confirmation…</h2>
            <p>This usually takes a few seconds. Keep this window open.</p>
          </>
        )}
        {(status === "unknown" || (status === "pending" && attempts >= POLL_MAX_ATTEMPTS)) && (
          <>
            <div style={{ fontSize: 48 }}>ℹ️</div>
            <h2>Still processing</h2>
            <p>
              We have not received the confirmation yet. It is safe to close this window — your
              payment will be reflected once the gateway confirms it.
            </p>
          </>
        )}
      </Card>
    </div>
  );
}
