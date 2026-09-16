import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "../components/ui/AppLayout";
import { Badge, Card } from "../components/ui";
import { paymentsApi } from "../api/client";
import { formatCents, formatDateTime } from "../lib/format";

/**
 * Scaffolded page — payment fields and a placeholder QR render are wired
 * to mock/API data. Once the real Pagopar QR payload format is confirmed,
 * swap the inline SVG placeholder for a real QR-code renderer.
 */
export function PaymentDetailPage() {
  const { paymentId } = useParams<{ paymentId: string }>();
  const paymentQuery = useQuery({
    queryKey: ["payment", paymentId],
    queryFn: () => paymentsApi.payments.get(paymentId!),
    enabled: Boolean(paymentId),
  });

  if (paymentQuery.isLoading) {
    return <p className="state-message">Loading payment…</p>;
  }

  const payment = paymentQuery.data;
  if (!payment) {
    return <p className="state-message error">Payment not found.</p>;
  }

  return (
    <div>
      <PageHeader
        title={`Payment #${payment.id}`}
        description={`${payment.customerName} · ${formatDateTime(payment.createdAt)}`}
        actions={<Badge tone={payment.status} />}
      />

      <div className="two-col">
        <Card>
          <h3 style={{ marginBottom: 14 }}>Details</h3>
          <div className="stat-row">
            <div>
              <div className="stat-card-label">Amount</div>
              <div>{formatCents(payment.amountCents, payment.currency)}</div>
            </div>
            <div>
              <div className="stat-card-label">Method</div>
              <div>{payment.method}</div>
            </div>
            <div>
              <div className="stat-card-label">Gateway ref</div>
              <div>
                <span className="code-pill">{payment.gatewayRef}</span>
              </div>
            </div>
          </div>
          <div className="stat-row">
            <div>
              <div className="stat-card-label">Customer</div>
              <div>{payment.customerName}</div>
            </div>
            <div>
              <div className="stat-card-label">Subscription</div>
              <div>{payment.subscriptionPlan ?? "—"}</div>
            </div>
            <div>
              <div className="stat-card-label">Invoice</div>
              <div>
                <span className="code-pill">{payment.invoiceRef}</span>
              </div>
            </div>
          </div>
        </Card>
        <Card style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12 }}>
          <h3 style={{ alignSelf: "flex-start" }}>Payment QR</h3>
          <div className="qr-box">
            {/* Placeholder QR glyph — replace with a real QR renderer against payment.qrPayload */}
            <svg width="140" height="140" viewBox="0 0 140 140">
              <rect width="140" height="140" fill="#fff" />
              <g fill="#0b0f17">
                <rect x="8" y="8" width="30" height="30" />
                <rect x="102" y="8" width="30" height="30" />
                <rect x="8" y="102" width="30" height="30" />
                <rect x="50" y="20" width="10" height="10" />
                <rect x="70" y="20" width="10" height="10" />
                <rect x="60" y="50" width="10" height="10" />
                <rect x="80" y="60" width="10" height="10" />
                <rect x="100" y="60" width="10" height="10" />
                <rect x="50" y="80" width="10" height="10" />
                <rect x="70" y="90" width="10" height="10" />
                <rect x="90" y="100" width="10" height="10" />
                <rect x="110" y="90" width="10" height="10" />
              </g>
            </svg>
          </div>
          <p style={{ color: "var(--text-dim)", fontSize: 12, textAlign: "center" }}>
            {payment.qrPayload ?? "Scan to view payment status via Pagopar"}
          </p>
        </Card>
      </div>
    </div>
  );
}
