import { Link } from "react-router-dom";
import { Badge, Card, Table } from "../../components/ui";
import { formatDate, formatPyg } from "../../lib/format";
import type { Payment } from "../../api/types";

export function RecentPaymentsTable({ payments }: { payments: Payment[] }) {
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Subscription</th>
            <th>Amount</th>
            <th>Gateway</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {payments.map((payment) => (
            <tr key={payment.id}>
              <td>{formatDate(payment.created_at)}</td>
              <td>#{payment.subscription}</td>
              <td>
                <Link to={`/payments/${payment.id}`}>{formatPyg(payment.amount_pyg)}</Link>
              </td>
              <td>{payment.gateway}</td>
              <td>
                <Badge tone={payment.status} />
              </td>
            </tr>
          ))}
          {payments.length === 0 && (
            <tr>
              <td colSpan={5} className="state-message">
                No payments yet.
              </td>
            </tr>
          )}
        </tbody>
      </Table>
    </Card>
  );
}
