import "./Badge.css";

export type BadgeTone = "active" | "trial" | "past_due" | "canceled" | "pending" | "succeeded" | "failed" | "refunded" | "draft" | "sent" | "signed" | "void" | "disabled" | "neutral";

const LABELS: Partial<Record<BadgeTone, string>> = {
  past_due: "past due",
};

export function Badge({ tone, children }: { tone: BadgeTone; children?: React.ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children ?? LABELS[tone] ?? tone}</span>;
}
