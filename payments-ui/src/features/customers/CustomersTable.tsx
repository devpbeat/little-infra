import { Link } from "react-router-dom";
import { Badge, Card, Table } from "../../components/ui";
import { formatDate } from "../../lib/format";
import type { Customer } from "../../api/types";

export function CustomersTable({ customers }: { customers: Customer[] }) {
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <th>Customer</th>
            <th>Email</th>
            <th>Contract status</th>
            <th>Subscription</th>
            <th>Customer since</th>
          </tr>
        </thead>
        <tbody>
          {customers.map((customer) => (
            <tr key={customer.external_ref}>
              <td>
                <Link to={`/customers/${encodeURIComponent(customer.external_ref)}`} className="table-link">
                  {customer.display_name || customer.external_ref}
                </Link>
              </td>
              <td>{customer.email || "—"}</td>
              <td>{customer.contract ? <Badge tone={customer.contract.status} /> : "—"}</td>
              <td>{customer.subscription ? <Badge tone={customer.subscription.status} /> : "—"}</td>
              <td>{formatDate(customer.created_at)}</td>
            </tr>
          ))}
          {customers.length === 0 && (
            <tr>
              <td colSpan={5} className="state-message">
                No customers yet.
              </td>
            </tr>
          )}
        </tbody>
      </Table>
    </Card>
  );
}
