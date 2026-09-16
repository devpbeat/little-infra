import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "../components/ui/AppLayout";
import { Badge, Button, Card, Table } from "../components/ui";
import { paymentsApi } from "../api/client";
import { formatCents, formatDate, formatDealType } from "../lib/format";
import { CustomerTimeline } from "../features/customers/CustomerTimeline";

export function CustomerDetailPage() {
  const { customerId } = useParams<{ customerId: string }>();
  const customerQuery = useQuery({
    queryKey: ["customer", customerId],
    queryFn: () => paymentsApi.customers.get(customerId!),
    enabled: Boolean(customerId),
  });

  if (customerQuery.isLoading) {
    return <p className="state-message">Loading customer…</p>;
  }

  const customer = customerQuery.data;
  if (!customer) {
    return <p className="state-message error">Customer not found.</p>;
  }

  return (
    <div>
      <PageHeader
        title={customer.name}
        description={`${customer.email} · Customer since ${formatDate(customer.createdAt)}`}
        actions={<Button variant="secondary">Edit</Button>}
      />

      <div className="stat-row">
        <Card>
          <div className="stat-card-label">Contract</div>
          <div>
            {formatDealType(customer.dealType)} · <Badge tone={customer.contractStatus} />
          </div>
        </Card>
        <Card>
          <div className="stat-card-label">Subscription</div>
          <div>{customer.subscriptionStatus ? <Badge tone={customer.subscriptionStatus} /> : "—"}</div>
        </Card>
        <Card>
          <div className="stat-card-label">Lifetime paid</div>
          <div>{formatCents(customer.lifetimePaidCents)}</div>
        </Card>
      </div>

      <div className="two-col">
        <div>
          <div className="section-title">Status Timeline</div>
          <CustomerTimeline events={customer.timeline} />
        </div>
        <div>
          <div className="section-title">Recent Payments</div>
          <Card>
            <Table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {customer.payments.map((payment) => (
                  <tr key={payment.id}>
                    <td>{formatDate(payment.createdAt)}</td>
                    <td>{formatCents(payment.amountCents, payment.currency)}</td>
                    <td>
                      <Badge tone={payment.status} />
                    </td>
                  </tr>
                ))}
                {customer.payments.length === 0 && (
                  <tr>
                    <td colSpan={3} className="state-message">
                      No payments yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </Table>
          </Card>
        </div>
      </div>
    </div>
  );
}
