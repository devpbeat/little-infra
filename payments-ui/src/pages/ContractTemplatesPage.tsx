import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "../components/ui/AppLayout";
import { Button, Card } from "../components/ui";
import { paymentsApi } from "../api/client";

const PREVIEW_VALUES: Record<string, string> = {
  company_name: "Ignite Solutions",
  customer_name: "Acme Corp",
  contract_date: "2026-09-16",
  plan_name: "SaaS Monthly",
  billing_amount: "$149.00",
  project_scope: "Custom internal tooling build",
  total_fee: "$4,500.00",
  hosting_fee: "$99.00",
};

function renderPreview(body: string): string {
  return body.replace(/\{\{(\w+)\}\}/g, (_, key: string) => PREVIEW_VALUES[key] ?? `{{${key}}}`);
}

/**
 * Scaffolded page — deal-type selection, source editor, and rendered
 * placeholder preview are wired to mock/API data. The "AI-generate" action
 * is a placeholder (stretch goal per the delivery brief) since no backend
 * endpoint for it is defined yet.
 */
export function ContractTemplatesPage() {
  const templatesQuery = useQuery({ queryKey: ["contract-templates"], queryFn: paymentsApi.contractTemplates.list });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draftBody, setDraftBody] = useState<string | null>(null);

  const selected = useMemo(
    () => templatesQuery.data?.find((t) => t.id === selectedId) ?? templatesQuery.data?.[0],
    [templatesQuery.data, selectedId],
  );

  const body = draftBody ?? selected?.body ?? "";

  return (
    <div>
      <PageHeader
        title="Contract Templates"
        description="Manage the three deal-type templates used to generate customer contracts"
        actions={<Button title="Placeholder action — no backend endpoint yet">✨ AI-generate</Button>}
      />

      {templatesQuery.isLoading && <p className="state-message">Loading templates…</p>}

      {templatesQuery.data && (
        <>
          <div className="deal-cards">
            {templatesQuery.data.map((template) => (
              <Card
                key={template.id}
                className={template.id === selected?.id ? "selected" : undefined}
                onClick={() => {
                  setSelectedId(template.id);
                  setDraftBody(null);
                }}
              >
                <h3>{template.name}</h3>
                <p>{template.description}</p>
              </Card>
            ))}
          </div>

          {selected && (
            <div className="editor-panel">
              <Card>
                <h3 style={{ marginBottom: 10 }}>Template source</h3>
                <textarea
                  className="editor-textarea"
                  value={body}
                  onChange={(e) => setDraftBody(e.target.value)}
                />
              </Card>
              <Card>
                <h3 style={{ marginBottom: 10 }}>Rendered preview</h3>
                <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: 13 }}>{renderPreview(body)}</div>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}
