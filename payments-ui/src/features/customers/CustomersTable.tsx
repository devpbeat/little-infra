import { Link } from "react-router-dom";
import { Badge, Card, Table } from "../../components/ui";
import { formatCents, formatDealType } from "../../lib/format";
import type { Customer } from "../../api/types";

export function CustomersTable({ customers }: { customers: Customer[] }) {
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <th>Customer</th>
            <th>Deal type</th>
            <th>Contract status</th>
            <th>Subscription</th>
            <th>Lifetime paid</th>
          </tr>
        </thead>
        <tbody>
          {customers.map((customer) => (
            <tr key={customer.id}>
              <td>
                <Link to={`/customers/${customer.id}`} className="table-link">
                  {customer.name}
                </Link>
              </td>
              <td>{formatDealType(customer.dealType)}</td>
              <td>
                <Badge tone={customer.contractStatus} />
              </td>
              <td>{customer.subscriptionStatus ? <Badge tone={customer.subscriptionStatus} /> : "—"}</td>
              <td>{formatCents(customer.lifetimePaidCents)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}
