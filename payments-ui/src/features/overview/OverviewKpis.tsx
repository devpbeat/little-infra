import { StatCard } from "../../components/ui";
import { formatPyg } from "../../lib/format";
import type { Payment, Subscription } from "../../api/types";

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;

/**
 * KPIs derived client-side from `/subscriptions` and `/payments` — the real
 * API has no `/overview` aggregate endpoint, so this replaces the mocked
 * summary with numbers computed from data the dashboard already fetches.
 */
export function OverviewKpis({ subscriptions, payments }: { subscriptions: Subscription[]; payments: Payment[] }) {
  const activeSubscriptions = subscriptions.filter((s) => s.status === "active").length;
  const now = Date.now();
  const trialsEndingSoon = subscriptions.filter(
    (s) => s.status === "trialing" && s.trial_end && new Date(s.trial_end).getTime() - now < SEVEN_DAYS_MS,
  ).length;
  const confirmedPayments = payments.filter((p) => p.status === "confirmed");
  const confirmedTotalPyg = confirmedPayments.reduce((sum, p) => sum + p.amount_pyg, 0);
  const successRate = payments.length ? confirmedPayments.length / payments.length : 0;

  return (
    <div className="kpi-grid">
      <StatCard label="Active Subscriptions" value={String(activeSubscriptions)} delta="Live count" deltaTone="neutral" />
      <StatCard label="Trials Ending Soon" value={String(trialsEndingSoon)} delta="within 7 days" deltaTone="neutral" />
      <StatCard label="Confirmed revenue" value={formatPyg(confirmedTotalPyg)} delta="Sum of confirmed payments" deltaTone="neutral" />
      <StatCard
        label={`Payments (${payments.length})`}
        value={String(confirmedPayments.length)}
        delta={`${(successRate * 100).toFixed(1)}% confirmed`}
      />
    </div>
  );
}
