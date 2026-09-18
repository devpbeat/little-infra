import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "../components/ui/AppLayout";
import { Badge, Button, Card, Table } from "../components/ui";
import { ADMIN_BASE_URL } from "../api/config";
import { httpClient, ApiError } from "../api/httpClient";

interface ApiKeyRow {
  id: number;
  prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

interface ConsumingAppRow {
  id: number;
  name: string;
  is_active: boolean;
  trial_days: number;
  created_at: string;
  api_keys: ApiKeyRow[];
}

/**
 * Staff-session-only management: issuing and revoking keys goes through
 * /api/v1/apps/ (admin sessions, never API keys). App creation itself
 * (with contract template + plan wiring) stays in Django admin.
 */
export function AppsKeysPage() {
  const queryClient = useQueryClient();
  const [issuedKey, setIssuedKey] = useState<{ app: string; key: string } | null>(null);

  const apps = useQuery({
    queryKey: ["apps"],
    queryFn: () =>
      httpClient.get<{ results: ConsumingAppRow[] }>("/apps/").then((r) => r.results),
  });

  const issue = useMutation({
    mutationFn: (app: ConsumingAppRow) =>
      httpClient
        .post<{ api_key: string }>(`/apps/${app.id}/issue-key/`)
        .then((r) => ({ app: app.name, key: r.api_key })),
    onSuccess: (result) => {
      setIssuedKey(result);
      queryClient.invalidateQueries({ queryKey: ["apps"] });
    },
  });

  const revoke = useMutation({
    mutationFn: ({ appId, prefix }: { appId: number; prefix: string }) =>
      httpClient.post(`/apps/${appId}/revoke-key/`, { prefix }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["apps"] }),
  });

  return (
    <div>
      <PageHeader
        title="Consuming Apps & API Keys"
        description="Issue and revoke machine keys; app creation (plan + contract template) lives in Django admin"
        actions={
          <a href={`${ADMIN_BASE_URL}apps_registry/consumingapp/add/`} target="_blank" rel="noreferrer">
            <Button variant="secondary">+ New app (admin)</Button>
          </a>
        }
      />

      {issuedKey && (
        <Card style={{ marginBottom: 16, borderColor: "var(--success, #4ade80)" }}>
          <h3 style={{ marginTop: 0 }}>New key for {issuedKey.app} — copy it NOW</h3>
          <p style={{ fontSize: 13, color: "var(--text-dim)" }}>
            This is the only time the full key is shown. It is stored hashed and cannot be
            recovered — only revoked and reissued.
          </p>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <code className="code-pill" style={{ userSelect: "all", overflowWrap: "anywhere" }}>
              {issuedKey.key}
            </code>
            <Button onClick={() => navigator.clipboard.writeText(issuedKey.key)}>Copy</Button>
            <Button variant="secondary" onClick={() => setIssuedKey(null)}>
              Done
            </Button>
          </div>
        </Card>
      )}

      {apps.isError && (
        <p className="state-message error">
          {apps.error instanceof ApiError && apps.error.status === 403
            ? "Admin session required — key management is not available in API-key mode."
            : "Failed to load apps."}
        </p>
      )}

      {(apps.data ?? []).map((app) => (
        <Card key={app.id} style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0 }}>
              {app.name} <Badge tone={app.is_active ? "active" : "canceled"} />
            </h3>
            <Button disabled={issue.isPending} onClick={() => issue.mutate(app)}>
              Issue new key
            </Button>
          </div>
          <Table>
            <thead>
              <tr>
                <th>Prefix</th>
                <th>Status</th>
                <th>Last used</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {app.api_keys.map((key) => (
                <tr key={key.id}>
                  <td>
                    <span className="code-pill">{key.prefix}</span>
                  </td>
                  <td>{key.revoked_at ? "Revoked" : key.is_active ? "Active" : "Inactive"}</td>
                  <td>{key.last_used_at ? new Date(key.last_used_at).toLocaleString() : "never"}</td>
                  <td>
                    {!key.revoked_at && (
                      <Button
                        variant="secondary"
                        disabled={revoke.isPending}
                        onClick={() => revoke.mutate({ appId: app.id, prefix: key.prefix })}
                      >
                        Revoke
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
              {app.api_keys.length === 0 && (
                <tr>
                  <td colSpan={4} className="state-message">
                    No keys issued yet.
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        </Card>
      ))}
    </div>
  );
}
