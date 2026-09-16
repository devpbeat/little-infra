import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "../components/ui/AppLayout";
import { Button } from "../components/ui";
import { paymentsApi } from "../api/client";
import { OverviewKpis } from "../features/overview/OverviewKpis";
import { SubscriptionsTable } from "../features/overview/SubscriptionsTable";
import { RecentPaymentsTable } from "../features/overview/RecentPaymentsTable";

export function OverviewPage() {
  const summaryQuery = useQuery({ queryKey: ["overview"], queryFn: paymentsApi.overview.get });
  const subscriptionsQuery = useQuery({ queryKey: ["subscriptions"], queryFn: paymentsApi.subscriptions.list });
  const paymentsQuery = useQuery({ queryKey: ["payments"], queryFn: paymentsApi.payments.list });

  return (
    <div>
      <PageHeader
        title="Overview"
        description="Live snapshot of subscriptions, trials, and payments"
        actions={<Button variant="secondary">Export report</Button>}
      />

      {summaryQuery.data && <OverviewKpis summary={summaryQuery.data} />}

      <div className="section-title">Active Subscriptions</div>
      {subscriptionsQuery.isLoading && <p className="state-message">Loading subscriptions…</p>}
      {subscriptionsQuery.data && <SubscriptionsTable subscriptions={subscriptionsQuery.data} />}

      <div className="section-title">Recent Payments</div>
      {paymentsQuery.isLoading && <p className="state-message">Loading payments…</p>}
      {paymentsQuery.data && <RecentPaymentsTable payments={paymentsQuery.data} />}
    </div>
  );
}
