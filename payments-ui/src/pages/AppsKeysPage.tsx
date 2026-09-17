import { PageHeader } from "../components/ui/AppLayout";
import { Button, Card } from "../components/ui";
import { ADMIN_BASE_URL } from "../api/config";

/**
 * Consuming-app and API-key management has no REST endpoints by design
 * (see `payments/` design notes) — apps and keys are provisioned via the
 * `issue_api_key` management command and the Django admin. This screen
 * intentionally does not fake a CRUD API; it links out to the real admin.
 */
export function AppsKeysPage() {
  return (
    <div>
      <PageHeader
        title="Consuming Apps & API Keys"
        description="Managed outside this dashboard — no REST API exists for this by design"
      />

      <Card style={{ maxWidth: 640 }}>
        <p style={{ marginBottom: 14, lineHeight: 1.6 }}>
          Consuming apps and their API keys are provisioned via the{" "}
          <code className="code-pill">issue_api_key</code> Django management command and managed in the
          Django admin. This dashboard does not expose (and will not fake) a REST API for creating,
          rotating, or revoking API keys — that surface is intentionally admin-only to keep key material
          out of a browser-reachable endpoint.
        </p>
        <a href={`${ADMIN_BASE_URL}apps_registry/consumingapp/`} target="_blank" rel="noreferrer">
          <Button>Open Consuming Apps in Django admin</Button>
        </a>
      </Card>
    </div>
  );
}
