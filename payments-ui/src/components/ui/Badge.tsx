import "./Badge.css";

export type BadgeTone =
  | "active"
  | "trialing"
  | "past_due"
  | "canceled"
  | "pending"
  | "confirmed"
  | "failed"
  | "expired"
  | "draft"
  | "generated"
  | "sent"
  | "signed"
  | "declined"
  | "voided"
  | "terminated"
  | "disabled"
  | "neutral";

const LABELS: Partial<Record<BadgeTone, string>> = {
  past_due: "past due",
};

export function Badge({ tone, children }: { tone: BadgeTone; children?: React.ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children ?? LABELS[tone] ?? tone}</span>;
}
