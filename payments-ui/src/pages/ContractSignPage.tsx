import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { marked } from "marked";
import { Button, Card } from "../components/ui";
import { API_BASE_URL } from "../api/config";

interface SigningDoc {
  status: string;
  template: string;
  client_name: string;
  markdown: string;
  signed_at: string | null;
}

/**
 * Public click-to-sign ceremony (`/contracts/sign/:token`). The token is
 * the capability; no login or API key. The document shown is the frozen
 * snapshot taken when the contract was sent.
 */
export function ContractSignPage() {
  const { token } = useParams<{ token: string }>();
  const [signerName, setSignerName] = useState("");
  const [signerDocumentId, setSignerDocumentId] = useState("");
  const [accepted, setAccepted] = useState(false);

  const doc = useQuery({
    queryKey: ["signing-doc", token],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/public/contract-signing/${token}/`);
      if (!res.ok) throw new Error(String(res.status));
      return (await res.json()) as SigningDoc;
    },
    enabled: Boolean(token),
    retry: false,
  });

  const sign = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE_URL}/public/contract-signing/${token}/sign/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          signer_name: signerName,
          signer_document_id: signerDocumentId,
          accepted,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail ?? "Signing failed.");
      return data as { status: string; signed_at: string };
    },
  });

  if (doc.isPending) return <p className="state-message">Loading contract…</p>;
  if (doc.isError)
    return (
      <div style={{ maxWidth: 560, margin: "10vh auto" }}>
        <Card>
          <h2>Contract not found</h2>
          <p>This signing link is invalid or no longer available.</p>
        </Card>
      </div>
    );

  const isSigned = sign.data?.status === "signed" || doc.data.status === "signed";

  return (
    <div style={{ maxWidth: 860, margin: "4vh auto", padding: "0 16px" }}>
      <Card>
        <h2 style={{ marginTop: 0 }}>{doc.data.template}</h2>
        <div
          style={{
            background: "#fff",
            color: "#111",
            padding: "32px 40px",
            borderRadius: 8,
            maxHeight: "55vh",
            overflowY: "auto",
            fontFamily: "Georgia, serif",
            lineHeight: 1.6,
          }}
          // Rendered from the operator-authored template snapshot.
          dangerouslySetInnerHTML={{ __html: marked.parse(doc.data.markdown) as string }}
        />
      </Card>

      <Card style={{ marginTop: 16 }}>
        {isSigned ? (
          <>
            <h3 style={{ marginTop: 0, color: "var(--success, #4ade80)" }}>
              ✅ Contract signed
            </h3>
            <p>
              Signed{doc.data.signed_at ? ` on ${new Date(doc.data.signed_at).toLocaleString()}` : ""}.
              You can close this window.
            </p>
          </>
        ) : (
          <>
            <h3 style={{ marginTop: 0 }}>Sign this contract</h3>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <label style={{ flex: 2, minWidth: 220 }}>
                <div className="stat-card-label">Full legal name</div>
                <input
                  className="text-input"
                  value={signerName}
                  onChange={(e) => setSignerName(e.target.value)}
                />
              </label>
              <label style={{ flex: 1, minWidth: 140 }}>
                <div className="stat-card-label">CI / RUC</div>
                <input
                  className="text-input"
                  value={signerDocumentId}
                  onChange={(e) => setSignerDocumentId(e.target.value)}
                />
              </label>
            </div>
            <label style={{ display: "flex", gap: 8, alignItems: "center", margin: "14px 0" }}>
              <input
                type="checkbox"
                checked={accepted}
                onChange={(e) => setAccepted(e.target.checked)}
              />
              <span style={{ fontSize: 14 }}>
                I have read the contract above and accept its terms (electronic signature,
                Law 4017/2010).
              </span>
            </label>
            {sign.isError && (
              <p className="state-message error">{(sign.error as Error).message}</p>
            )}
            <Button
              disabled={sign.isPending || !signerName || !signerDocumentId || !accepted}
              onClick={() => sign.mutate()}
            >
              {sign.isPending ? "Signing…" : "Accept and sign"}
            </Button>
          </>
        )}
      </Card>
    </div>
  );
}
