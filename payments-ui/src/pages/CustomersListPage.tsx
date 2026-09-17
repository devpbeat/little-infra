import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/ui/AppLayout";
import { Button } from "../components/ui";
import { paymentsApi } from "../api/client";
import { CustomersTable } from "../features/customers/CustomersTable";

export function CustomersListPage() {
  const customersQuery = useQuery({ queryKey: ["customers"], queryFn: paymentsApi.customers.list });

  return (
    <div>
      <PageHeader
        title="Customers"
        description="All accounts with a contract, subscription, or payment history"
        actions={
          <Link to="/customers/new">
            <Button>+ New customer</Button>
          </Link>
        }
      />

      {customersQuery.isLoading && <p className="state-message">Loading customers…</p>}
      {customersQuery.isError && <p className="state-message error">Failed to load customers.</p>}
      {customersQuery.data && <CustomersTable customers={customersQuery.data.results} />}
    </div>
  );
}
