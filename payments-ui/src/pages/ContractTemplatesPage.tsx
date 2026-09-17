import { PageHeader } from "../components/ui/AppLayout";
import { Button, Card } from "../components/ui";
import { ADMIN_BASE_URL } from "../api/config";

/**
 * Contract templates have no REST endpoints either — same reasoning as
 * Apps & Keys: they're seed/admin-managed data (`ContractTemplate` model),
 * not something a consuming app or this dashboard mutates over the API.
 */
export function ContractTemplatesPage() {
  return (
    <div>
      <PageHeader
        title="Contract Templates"
        description="Managed in the Django admin — no REST API exists for this by design"
      />

      <Card style={{ maxWidth: 640 }}>
        <p style={{ marginBottom: 14, lineHeight: 1.6 }}>
          Contract templates back the deal-type contracts generated on customer signup. They are
          created and edited directly in the Django admin rather than through this dashboard.
        </p>
        <a href={`${ADMIN_BASE_URL}contracts/contracttemplate/`} target="_blank" rel="noreferrer">
          <Button>Open Contract Templates in Django admin</Button>
        </a>
      </Card>
    </div>
  );
}
