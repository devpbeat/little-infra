import type { Customer, Payment, Subscription } from "../api/types";

/**
 * Fixture data shaped exactly like the real payments API responses
 * (reconciled against `/api/schema`), used only when the mock adapter is
 * active (`src/api/config.ts`).
 */

export const mockSubscriptions: Subscription[] = [
  {
    id: 1,
    customer: 1,
    plan: 1,
    status: "active",
    trial_start: "2026-02-20T00:00:00Z",
    trial_end: "2026-03-02T00:00:00Z",
    current_period_end: "2026-10-01T00:00:00Z",
    canceled_at: null,
    created_at: "2026-03-02T00:00:00Z",
  },
  {
    id: 2,
    customer: 2,
    plan: 2,
    status: "active",
    trial_start: "2026-01-01T00:00:00Z",
    trial_end: "2026-01-10T00:00:00Z",
    current_period_end: "2027-01-14T00:00:00Z",
    canceled_at: null,
    created_at: "2026-01-10T00:00:00Z",
  },
  {
    id: 3,
    customer: 3,
    plan: 1,
    status: "trialing",
    trial_start: "2026-09-08T00:00:00Z",
    trial_end: "2026-09-22T00:00:00Z",
    current_period_end: null,
    canceled_at: null,
    created_at: "2026-09-08T00:00:00Z",
  },
  {
    id: 4,
    customer: 5,
    plan: 1,
    status: "past_due",
    trial_start: "2025-12-01T00:00:00Z",
    trial_end: "2025-12-15T00:00:00Z",
    current_period_end: "2026-09-12T00:00:00Z",
    canceled_at: null,
    created_at: "2025-12-15T00:00:00Z",
  },
];

export const mockPayments: Payment[] = [
  {
    id: 20894,
    subscription: 1,
    amount_pyg: 1_090_000,
    status: "confirmed",
    gateway: "pagopar",
    gateway_order_id: "pgp_9f2ac3",
    checkout_url: "https://pagopar.example.com/checkout/pgp_9f2ac3",
    created_at: "2026-09-15T14:22:00Z",
    updated_at: "2026-09-15T14:25:00Z",
    confirmed_at: "2026-09-15T14:25:00Z",
  },
  {
    id: 20871,
    subscription: 2,
    amount_pyg: 720_000,
    status: "confirmed",
    gateway: "pagopar",
    gateway_order_id: "pgp_7a11bd",
    checkout_url: "https://pagopar.example.com/checkout/pgp_7a11bd",
    created_at: "2026-09-14T09:03:00Z",
    updated_at: "2026-09-14T09:05:00Z",
    confirmed_at: "2026-09-14T09:05:00Z",
  },
  {
    id: 20855,
    subscription: 4,
    amount_pyg: 1_450_000,
    status: "failed",
    gateway: "pagopar",
    gateway_order_id: "pgp_44f0e2",
    checkout_url: "",
    created_at: "2026-09-13T18:40:00Z",
    updated_at: "2026-09-13T18:41:00Z",
    confirmed_at: null,
  },
  {
    id: 20812,
    subscription: 3,
    amount_pyg: 450_000,
    status: "pending",
    gateway: "pagopar",
    gateway_order_id: "pgp_a02c19",
    checkout_url: "https://pagopar.example.com/checkout/pgp_a02c19",
    created_at: "2026-09-11T11:15:00Z",
    updated_at: "2026-09-11T11:15:00Z",
    confirmed_at: null,
  },
];

export const mockCustomers: Customer[] = [
  {
    external_ref: "cus_acme",
    display_name: "Acme Corp",
    email: "billing@acme.example.com",
    created_at: "2026-03-02T00:00:00Z",
    contract: { id: 1, status: "signed", external_envelope_id: "env-1", created_at: "2026-03-02T00:00:00Z", signed_at: "2026-03-03T00:00:00Z" },
    subscription: { id: 1, status: "active", trial_start: "2026-02-20T00:00:00Z", trial_end: "2026-03-02T00:00:00Z", current_period_end: "2026-10-01T00:00:00Z" },
  },
  {
    external_ref: "cus_nordic",
    display_name: "Nordic Labs",
    email: "ops@nordiclabs.example.com",
    created_at: "2026-01-10T00:00:00Z",
    contract: { id: 2, status: "signed", external_envelope_id: "env-2", created_at: "2026-01-10T00:00:00Z", signed_at: "2026-01-11T00:00:00Z" },
    subscription: { id: 2, status: "active", trial_start: "2026-01-01T00:00:00Z", trial_end: "2026-01-10T00:00:00Z", current_period_end: "2027-01-14T00:00:00Z" },
  },
  {
    external_ref: "cus_vera",
    display_name: "Vera Studio",
    email: "hello@vera.example.com",
    created_at: "2026-09-08T00:00:00Z",
    contract: { id: 3, status: "sent", external_envelope_id: "env-3", created_at: "2026-09-08T00:00:00Z", signed_at: null },
    subscription: { id: 3, status: "trialing", trial_start: "2026-09-08T00:00:00Z", trial_end: "2026-09-22T00:00:00Z", current_period_end: null },
  },
  {
    external_ref: "cus_kilo",
    display_name: "Kilo Systems",
    email: "finance@kilosystems.example.com",
    created_at: "2026-08-01T00:00:00Z",
    contract: { id: 4, status: "signed", external_envelope_id: "env-4", created_at: "2026-08-01T00:00:00Z", signed_at: "2026-08-02T00:00:00Z" },
    subscription: null,
  },
  {
    external_ref: "cus_blue",
    display_name: "Blue Harbor",
    email: "accounts@blueharbor.example.com",
    created_at: "2025-12-15T00:00:00Z",
    contract: { id: 5, status: "signed", external_envelope_id: "env-5", created_at: "2025-12-15T00:00:00Z", signed_at: "2025-12-16T00:00:00Z" },
    subscription: { id: 4, status: "past_due", trial_start: "2025-12-01T00:00:00Z", trial_end: "2025-12-15T00:00:00Z", current_period_end: "2026-09-12T00:00:00Z" },
  },
];
