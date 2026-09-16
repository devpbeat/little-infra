import { Link } from "react-router-dom";
import { Badge, Card, Table } from "../../components/ui";
import { formatCents, formatDate } from "../../lib/format";
import type { Payment } from "../../api/types";

export function RecentPaymentsTable({ payments }: { payments: Payment[] }) {
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Customer</th>
            <th>Amount</th>
            <th>Method</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {payments.map((payment) => (
            <tr key={payment.id}>
              <td>{formatDate(payment.createdAt)}</td>
              <td>{payment.customerName}</td>
              <td>
                <Link to={`/payments/${payment.id}`}>{formatCents(payment.amountCents, payment.currency)}</Link>
              </td>
              <td>{payment.method}</td>
              <td>
                <Badge tone={payment.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}
