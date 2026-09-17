import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { PageHeader } from "../components/ui/AppLayout";
import { Badge, Card } from "../components/ui";
import { paymentsApi } from "../api/client";
import { formatDateTime, formatPyg } from "../lib/format";

export function PaymentDetailPage() {
  const { paymentId } = useParams<{ paymentId: string }>();
  const paymentQuery = useQuery({
    queryKey: ["payment", paymentId],
    queryFn: () => paymentsApi.payments.get(Number(paymentId)),
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
        description={`Subscription #${payment.subscription} · ${formatDateTime(payment.created_at)}`}
        actions={<Badge tone={payment.status} />}
      />

      <div className="two-col">
        <Card>
          <h3 style={{ marginBottom: 14 }}>Details</h3>
          <div className="stat-row">
            <div>
              <div className="stat-card-label">Amount</div>
              <div>{formatPyg(payment.amount_pyg)}</div>
            </div>
            <div>
              <div className="stat-card-label">Gateway</div>
              <div>{payment.gateway}</div>
            </div>
            <div>
              <div className="stat-card-label">Gateway order id</div>
              <div>
                <span className="code-pill">{payment.gateway_order_id || "—"}</span>
              </div>
            </div>
          </div>
          <div className="stat-row">
            <div>
              <div className="stat-card-label">Subscription</div>
              <div>#{payment.subscription}</div>
            </div>
            <div>
              <div className="stat-card-label">Confirmed at</div>
              <div>{payment.confirmed_at ? formatDateTime(payment.confirmed_at) : "—"}</div>
            </div>
            <div>
              <div className="stat-card-label">Checkout URL</div>
              <div>
                {payment.checkout_url ? (
                  <a
                    href={payment.checkout_url}
                    rel="noreferrer"
                    onClick={(e) => {
                      // Open Pagopar in a small popup; the href stays as a
                      // plain-link fallback for popup blockers.
                      const win = window.open(
                        payment.checkout_url!,
                        "pagopar",
                        "width=480,height=760,popup"
                      );
                      if (win) e.preventDefault();
                    }}
                  >
                    Open checkout
                  </a>
                ) : (
                  "—"
                )}
              </div>
            </div>
          </div>
        </Card>
        <Card style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12 }}>
          <h3 style={{ alignSelf: "flex-start" }}>Payment QR</h3>
          <div className="qr-box">
            {payment.checkout_url ? (
              <QRCodeSVG value={payment.checkout_url} size={140} />
            ) : (
              <p style={{ color: "#0b0f17", fontSize: 12, padding: 8 }}>No checkout URL yet.</p>
            )}
          </div>
          <p style={{ color: "var(--text-dim)", fontSize: 12, textAlign: "center" }}>
            Scan to open the Pagopar checkout, or use the link above.
          </p>
        </Card>
      </div>
    </div>
  );
}
