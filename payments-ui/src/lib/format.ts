export function formatCents(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(cents / 100);
}

/** PYG (Paraguayan guaraní) has no minor unit — `amount_pyg` is already a whole-currency integer. */
export function formatPyg(amountPyg: number): string {
  return new Intl.NumberFormat("es-PY", { style: "currency", currency: "PYG", maximumFractionDigits: 0 }).format(
    amountPyg,
  );
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-US", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

const DEAL_TYPE_LABELS: Record<string, string> = {
  saas_monthly: "SaaS Monthly",
  saas_annual: "SaaS Annual",
  fixed_with_ownership: "Fixed (with ownership)",
  fixed_no_ownership_hosting: "Fixed (hosting, no ownership)",
};

export function formatDealType(dealType: string): string {
  return DEAL_TYPE_LABELS[dealType] ?? dealType;
}
