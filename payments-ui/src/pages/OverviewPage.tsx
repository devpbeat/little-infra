import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/ui/AppLayout";
import { Button } from "../components/ui";
import { paymentsApi } from "../api/client";
import { OverviewKpis } from "../features/overview/OverviewKpis";
import { SubscriptionsTable } from "../features/overview/SubscriptionsTable";
import { RecentPaymentsTable } from "../features/overview/RecentPaymentsTable";

export function OverviewPage() {
  const subscriptionsQuery = useQuery({ queryKey: ["subscriptions"], queryFn: paymentsApi.subscriptions.list });
  const paymentsQuery = useQuery({ queryKey: ["payments"], queryFn: paymentsApi.payments.list });

  return (
    <div>
      <PageHeader
        title="Overview"
        description="Live snapshot of subscriptions and payments"
        actions={
          <Link to="/customers/new">
            <Button>+ New customer</Button>
          </Link>
        }
      />

      {subscriptionsQuery.data && paymentsQuery.data && (
        <OverviewKpis subscriptions={subscriptionsQuery.data.results} payments={paymentsQuery.data.results} />
      )}

      <div className="section-title">Subscriptions</div>
      {subscriptionsQuery.isLoading && <p className="state-message">Loading subscriptions…</p>}
      {subscriptionsQuery.isError && <p className="state-message error">Failed to load subscriptions.</p>}
      {subscriptionsQuery.data && <SubscriptionsTable subscriptions={subscriptionsQuery.data.results} />}

      <div className="section-title">Recent Payments</div>
      {paymentsQuery.isLoading && <p className="state-message">Loading payments…</p>}
      {paymentsQuery.isError && <p className="state-message error">Failed to load payments.</p>}
      {paymentsQuery.data && <RecentPaymentsTable payments={paymentsQuery.data.results} />}
    </div>
  );
}
