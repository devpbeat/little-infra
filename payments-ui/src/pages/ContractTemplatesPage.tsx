import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "../components/ui/AppLayout";
import { Badge, Button, Card } from "../components/ui";
import { httpClient, ApiError } from "../api/httpClient";

interface TemplateRow {
  id: number;
  name: string;
  deal_type: string;
  body: string;
  is_approved: boolean;
  is_active: boolean;
  updated_at: string;
}

const DEAL_TYPES = [
  { value: "saas_subscription", label: "SaaS monthly/annual fee" },
  { value: "fixed_with_ownership", label: "Fixed price with code ownership" },
  { value: "fixed_hosted", label: "Fixed price, hosting provided" },
];

/** Staff-only: manage contract template markdown, preview, approve, AI-draft. */
export function ContractTemplatesPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draftBody, setDraftBody] = useState<string | null>(null);
  const [genForm, setGenForm] = useState({ name: "", deal_type: "saas_subscription", instructions: "" });
  const [preview, setPreview] = useState<string | null>(null);

  const templates = useQuery({
    queryKey: ["contract-templates"],
    queryFn: () =>
      httpClient
        .get<{ results: TemplateRow[] }>("/contract-templates/")
        .then((r) => r.results),
  });
  const selected = templates.data?.find((t) => t.id === selectedId) ?? null;

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["contract-templates"] });

  const save = useMutation({
    mutationFn: (t: TemplateRow) =>
      httpClient.patch(`/contract-templates/${t.id}/`, { body: draftBody ?? t.body }),
    onSuccess: () => {
      setDraftBody(null);
      invalidate();
    },
  });
  const approve = useMutation({
    mutationFn: (t: TemplateRow) =>
      httpClient.patch(`/contract-templates/${t.id}/`, { is_approved: !t.is_approved }),
    onSuccess: invalidate,
  });
  const loadPreview = useMutation({
    mutationFn: (t: TemplateRow) =>
      httpClient.get<{ markdown: string }>(`/contract-templates/${t.id}/preview/`),
    onSuccess: (r) => setPreview(r.markdown),
  });
  const generate = useMutation({
    mutationFn: () => httpClient.post<TemplateRow>("/contract-templates/generate/", genForm),
    onSuccess: (created) => {
      invalidate();
      setSelectedId(created.id);
      setPreview(null);
    },
  });

  return (
    <div>
      <PageHeader
        title="Contract Templates"
        description="Markdown legal documents with placeholders; AI drafts require human approval before use"
      />

      <Card style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0 }}>AI-generate a draft (Claude Opus)</h3>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
          <label>
            <div className="stat-card-label">Name</div>
            <input
              className="text-input"
              value={genForm.name}
              onChange={(e) => setGenForm({ ...genForm, name: e.target.value })}
            />
          </label>
          <label>
            <div className="stat-card-label">Deal type</div>
            <select
              className="text-input"
              value={genForm.deal_type}
              onChange={(e) => setGenForm({ ...genForm, deal_type: e.target.value })}
            >
              {DEAL_TYPES.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </select>
          </label>
          <label style={{ flexGrow: 1 }}>
            <div className="stat-card-label">Extra instructions (optional)</div>
            <input
              className="text-input"
              value={genForm.instructions}
              onChange={(e) => setGenForm({ ...genForm, instructions: e.target.value })}
            />
          </label>
          <Button disabled={generate.isPending || !genForm.name} onClick={() => generate.mutate()}>
            {generate.isPending ? "Drafting… (~30s)" : "Generate draft"}
          </Button>
        </div>
        {generate.isError && (
          <p style={{ color: "var(--danger, #f87171)", fontSize: 13 }}>
            {generate.error instanceof ApiError ? generate.error.message : "Generation failed."}
          </p>
        )}
      </Card>

      <div className="two-col">
        <Card>
          <h3 style={{ marginTop: 0 }}>Templates</h3>
          {(templates.data ?? []).map((t) => (
            <div
              key={t.id}
              onClick={() => {
                setSelectedId(t.id);
                setDraftBody(null);
                setPreview(null);
              }}
              style={{
                padding: "8px 10px",
                cursor: "pointer",
                borderRadius: 6,
                background: t.id === selectedId ? "rgba(91,141,239,0.15)" : undefined,
                display: "flex",
                justifyContent: "space-between",
                gap: 8,
              }}
            >
              <span>{t.name}</span>
              <Badge tone={t.is_approved ? "active" : "pending"} />
            </div>
          ))}
          {templates.data?.length === 0 && (
            <p className="state-message">No templates yet — generate or create one.</p>
          )}
          {templates.isError && (
            <p className="state-message error">Admin session required to manage templates.</p>
          )}
        </Card>

        <Card>
          {!selected && <p className="state-message">Select a template to edit.</p>}
          {selected && (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ margin: 0 }}>
                  {selected.name}{" "}
                  <span style={{ fontSize: 12, color: "var(--text-dim)" }}>
                    ({DEAL_TYPES.find((d) => d.value === selected.deal_type)?.label})
                  </span>
                </h3>
                <span style={{ display: "flex", gap: 8 }}>
                  <Button
                    variant="secondary"
                    disabled={loadPreview.isPending}
                    onClick={() => loadPreview.mutate(selected)}
                  >
                    Preview
                  </Button>
                  <Button
                    variant="secondary"
                    disabled={save.isPending || draftBody === null}
                    onClick={() => save.mutate(selected)}
                  >
                    Save
                  </Button>
                  <Button disabled={approve.isPending} onClick={() => approve.mutate(selected)}>
                    {selected.is_approved ? "Revoke approval" : "Approve"}
                  </Button>
                </span>
              </div>
              <textarea
                className="text-input"
                style={{ width: "100%", minHeight: 320, marginTop: 12, fontFamily: "monospace", fontSize: 13 }}
                value={draftBody ?? selected.body}
                onChange={(e) => setDraftBody(e.target.value)}
              />
              {preview !== null && (
                <div style={{ marginTop: 12 }}>
                  <div className="stat-card-label">Preview (sample data)</div>
                  <pre style={{ whiteSpace: "pre-wrap", fontSize: 13, background: "rgba(0,0,0,0.25)", padding: 12, borderRadius: 6 }}>
                    {preview}
                  </pre>
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
