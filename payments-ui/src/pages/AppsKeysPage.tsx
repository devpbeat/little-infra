import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "../components/ui/AppLayout";
import { Badge, Button, Card, Table } from "../components/ui";
import { paymentsApi } from "../api/client";
import { formatDate, formatDateTime } from "../lib/format";

/**
 * Scaffolded page — wired to the mock/API client for a working list view,
 * but key creation/rotation actions are placeholders (stretch goal per
 * the delivery brief).
 */
export function AppsKeysPage() {
  const appsQuery = useQuery({ queryKey: ["apps"], queryFn: paymentsApi.apps.list });

  return (
    <div>
      <PageHeader
        title="Consuming Apps & API Keys"
        description="Applications integrated with the payments API"
        actions={<Button>+ New App</Button>}
      />

      {appsQuery.isLoading && <p className="state-message">Loading apps…</p>}
      {appsQuery.data && (
        <Card>
          <Table>
            <thead>
              <tr>
                <th>App</th>
                <th>Environment</th>
                <th>API Key</th>
                <th>Created</th>
                <th>Last used</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {appsQuery.data.map((app) => (
                <tr key={app.id}>
                  <td>{app.name}</td>
                  <td>{app.environment}</td>
                  <td>
                    <span className="code-pill">{app.apiKeyMasked}</span>
                  </td>
                  <td>{formatDate(app.createdAt)}</td>
                  <td>{app.lastUsedAt ? formatDateTime(app.lastUsedAt) : "never"}</td>
                  <td>
                    <Badge tone={app.status} />
                  </td>
                  <td>
                    <Button variant="secondary">{app.status === "active" ? "Revoke" : "Enable"}</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      )}
    </div>
  );
}
