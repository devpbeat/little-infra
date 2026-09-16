/**
 * Domain types inferred from the payments service scaffold.
 *
 * At the time this client was written, `payments/` only exposes a health
 * check endpoint (`payments/config/urls.py`) — the domain endpoints
 * (customers, contracts, subscriptions, billing, webhooks) referenced in
 * `payments/env.example` ("Slices D and E") are not implemented yet.
 *
 * These types are inferred from:
 *  - `payments/env.example` (Pagopar as the payment gateway, DocuSign /
 *    NullContractSigner as the contract signer)
 *  - the 5 required admin screens (subscriptions, trials, payments,
 *    consuming apps + API keys, customers with contract timelines,
 *    contract templates for 3 deal types, payment detail + QR)
 *
 * Treat this file as the best-guess contract; align it with the real
 * OpenAPI schema once `payments/` publishes one at `/api/schema`.
 */

export type SubscriptionStatus = "trial" | "active" | "past_due" | "canceled";

export type PaymentStatus = "pending" | "succeeded" | "failed" | "refunded";

export type ContractStatus =
  | "draft"
  | "sent"
  | "signed"
  | "void";

export type DealType =
  | "saas_monthly"
  | "saas_annual"
  | "fixed_with_ownership"
  | "fixed_no_ownership_hosting";

export interface Customer {
  id: string;
  name: string;
  email: string;
  createdAt: string;
  dealType: DealType;
  contractStatus: ContractStatus;
  subscriptionStatus: SubscriptionStatus | null;
  lifetimePaidCents: number;
}

export interface Subscription {
  id: string;
  customerId: string;
  customerName: string;
  planName: string;
  status: SubscriptionStatus;
  renewalDate: string;
  mrrCents: number;
}

export interface Payment {
  id: string;
  customerId: string;
  customerName: string;
  amountCents: number;
  currency: string;
  method: string;
  status: PaymentStatus;
  gatewayRef: string;
  invoiceRef: string;
  subscriptionPlan?: string;
  qrPayload?: string;
  createdAt: string;
}

export interface TimelineEvent {
  id: string;
  date: string;
  title: string;
  kind: "contract" | "subscription" | "payment";
}

export interface CustomerDetail extends Customer {
  timeline: TimelineEvent[];
  payments: Payment[];
}

export interface ConsumingApp {
  id: string;
  name: string;
  environment: "production" | "staging";
  apiKeyMasked: string;
  createdAt: string;
  lastUsedAt: string | null;
  status: "active" | "disabled";
}

export interface ContractTemplate {
  id: string;
  dealType: DealType;
  name: string;
  description: string;
  body: string;
  updatedAt: string;
}

export interface OverviewSummary {
  activeSubscriptions: number;
  trialsEndingSoon: number;
  mrrCents: number;
  paymentsLast30d: number;
  paymentSuccessRate: number;
}
