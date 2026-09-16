import { StatCard } from "../../components/ui";
import { formatCents, formatPercent } from "../../lib/format";
import type { OverviewSummary } from "../../api/types";

export function OverviewKpis({ summary }: { summary: OverviewSummary }) {
  return (
    <div className="kpi-grid">
      <StatCard label="Active Subscriptions" value={String(summary.activeSubscriptions)} delta="Live count" deltaTone="neutral" />
      <StatCard
        label="Trials Ending Soon"
        value={String(summary.trialsEndingSoon)}
        delta="within 7 days"
        deltaTone="neutral"
      />
      <StatCard label="MRR" value={formatCents(summary.mrrCents)} delta="Monthly recurring revenue" deltaTone="neutral" />
      <StatCard
        label="Payments (30d)"
        value={String(summary.paymentsLast30d)}
        delta={`${formatPercent(summary.paymentSuccessRate)} success rate`}
      />
    </div>
  );
}
