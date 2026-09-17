import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../components/ui/AppLayout";
import { Button, Card } from "../components/ui";
import { paymentsApi } from "../api/client";
import { ApiError } from "../api/httpClient";

/**
 * Real write action: `POST /api/v1/customers/signup`. Idempotent by
 * (app, external_ref) on the backend — resubmitting the same external_ref
 * returns the existing customer instead of erroring.
 */
export function CustomerSignupPage() {
  const navigate = useNavigate();
  const [externalRef, setExternalRef] = useState("");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");

  const signup = useMutation({
    mutationFn: () => paymentsApi.customers.signup({ external_ref: externalRef, email, display_name: displayName }),
    onSuccess: (customer) => navigate(`/customers/${encodeURIComponent(customer.external_ref)}`),
  });

  return (
    <div>
      <PageHeader title="New customer" description="Signup a customer against the authenticated consuming app" />
      <Card style={{ maxWidth: 480 }}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            signup.mutate();
          }}
          style={{ display: "flex", flexDirection: "column", gap: 14 }}
        >
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

          <Button type="submit" disabled={signup.isPending || !externalRef}>
            {signup.isPending ? "Signing up…" : "Sign up customer"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
