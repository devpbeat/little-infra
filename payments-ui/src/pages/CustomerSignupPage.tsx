import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../components/ui/AppLayout";
import { Button, Card } from "../components/ui";
import { getStoredApiKey } from "../api/config";
import { httpClient } from "../api/httpClient";
import { paymentsApi } from "../api/client";
import { ApiError } from "../api/httpClient";

/**
 * Real write action: `POST /api/v1/customers/signup`. Idempotent by
 * (app, external_ref) on the backend — resubmitting the same external_ref
 * returns the existing customer instead of erroring.
 */
export function CustomerSignupPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [externalRef, setExternalRef] = useState("");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [appId, setAppId] = useState<number | "">("");

  // Staff sessions must pick which app the customer belongs to; API-key
  // mode has the app implied by the key and gets no selector.
  const isStaffMode = !getStoredApiKey();
  const apps = useQuery({
    queryKey: ["apps"],
    queryFn: () =>
      httpClient
        .get<{ results: { id: number; name: string }[] }>("/apps/")
        .then((r) => r.results),
    enabled: isStaffMode,
  });

  const signup = useMutation({
    mutationFn: () => {
      const payload = { external_ref: externalRef, email, display_name: displayName };
      return isStaffMode
        ? httpClient.post<{ external_ref: string }>(`/apps/${appId}/customers/`, payload)
        : paymentsApi.customers.signup(payload);
    },
    onSuccess: (customer) => {
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      navigate(`/customers/${encodeURIComponent(customer.external_ref)}`);
    },
  });

  return (
    <div>
      <PageHeader
        title="New customer"
        description={
          isStaffMode
            ? "Create a customer under an app — contract and trial provision automatically"
            : "Signup a customer against the authenticated consuming app"
        }
      />
      <Card style={{ maxWidth: 480 }}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            signup.mutate();
          }}
          style={{ display: "flex", flexDirection: "column", gap: 14 }}
        >
          {isStaffMode && (
            <label>
              <div className="stat-card-label">App (required)</div>
              <select
                className="text-input"
                value={appId}
                onChange={(e) => setAppId(e.target.value ? Number(e.target.value) : "")}
              >
                <option value="">Select an app…</option>
                {(apps.data ?? []).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            <div className="stat-card-label">External ref (required)</div>
            <input
              className="text-input"
              value={externalRef}
              onChange={(e) => setExternalRef(e.target.value)}
              required
              placeholder="e.g. cus_acme"
            />
          </label>
          <label>
            <div className="stat-card-label">Display name</div>
            <input className="text-input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </label>
          <label>
            <div className="stat-card-label">Email</div>
            <input
              className="text-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>

          {signup.isError && (
            <p className="state-message error">
              {signup.error instanceof ApiError ? signup.error.message : "Signup failed."}
            </p>
          )}

          <Button type="submit" disabled={signup.isPending || !externalRef || (isStaffMode && !appId)}>
            {signup.isPending ? "Signing up…" : "Sign up customer"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
