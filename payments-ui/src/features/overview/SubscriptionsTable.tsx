import { Badge, Card, Table } from "../../components/ui";
import { formatCents, formatDate } from "../../lib/format";
import type { Subscription } from "../../api/types";

export function SubscriptionsTable({ subscriptions }: { subscriptions: Subscription[] }) {
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <th>Customer</th>
            <th>Plan</th>
            <th>Status</th>
            <th>Renewal</th>
            <th>MRR</th>
          </tr>
        </thead>
        <tbody>
          {subscriptions.map((sub) => (
            <tr key={sub.id}>
              <td>{sub.customerName}</td>
              <td>{sub.planName}</td>
              <td>
                <Badge tone={sub.status} />
              </td>
              <td>{formatDate(sub.renewalDate)}</td>
              <td>{formatCents(sub.mrrCents)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}
