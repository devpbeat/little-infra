import { isUsingMockApi } from "./config";
import { httpClient } from "./httpClient";
import {
  mockCustomers,
  mockPayments,
  mockSubscriptions,
} from "../fixtures/data";
import type {
  Contract,
  ContractAppReportedStatus,
  Customer,
  Entitlement,
  PaginatedResponse,
  Payment,
  SignupRequest,
  Subscription,
} from "./types";

/** Small helper to keep mock responses feeling async without real network calls. */
function mockDelay<T>(value: T, ms = 150): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

function mockPage<T>(items: T[]): PaginatedResponse<T> {
  return { count: items.length, next: null, previous: null, results: items };
}

/**
 * Typed client for the real payments API, reconciled against the OpenAPI
 * schema exported from `payments/` (main tip) via `manage.py spectacular`.
 *
 * Endpoints with no REST surface by design (consuming-app / API-key CRUD,
 * contract-template CRUD) are intentionally absent here — see
 * `AppsKeysPage.tsx` and `ContractTemplatesPage.tsx`, which link to the
 * Django admin instead of calling a fake endpoint.
 */
export const paymentsApi = {
  customers: {
    list: (): Promise<PaginatedResponse<Customer>> =>
      isUsingMockApi() ? mockDelay(mockPage(mockCustomers)) : httpClient.get("/customers/"),
    get: (externalRef: string): Promise<Customer> =>
      isUsingMockApi()
        ? mockDelay(mockCustomers.find((c) => c.external_ref === externalRef)!)
        : httpClient.get(`/customers/${encodeURIComponent(externalRef)}/`),
    entitlement: (externalRef: string): Promise<Entitlement> =>
      isUsingMockApi()
        ? mockDelay({ entitled: true, status: "active", trial_end: null, current_period_end: null })
        : httpClient.get(`/customers/${encodeURIComponent(externalRef)}/entitlement/`),
    /** `POST /customers/signup` — idempotent by (app, external_ref); no trailing slash. */
    signup: (body: SignupRequest): Promise<Customer> =>
      isUsingMockApi()
        ? mockDelay({
            external_ref: body.external_ref,
            email: body.email ?? "",
            display_name: body.display_name ?? "",
            created_at: new Date().toISOString(),
            contract: null,
            subscription: null,
          })
        : httpClient.post("/customers/signup", body),
  },

  contracts: {
    list: (): Promise<PaginatedResponse<Contract>> =>
      isUsingMockApi() ? mockDelay(mockPage([])) : httpClient.get("/contracts/"),
    get: (id: number): Promise<Contract> =>
      isUsingMockApi() ? mockDelay({} as Contract) : httpClient.get(`/contracts/${id}/`),
    /** `POST /contracts/{id}/transition` — only `sent` and `signed` are app-reportable. */
    transition: (id: number, status: ContractAppReportedStatus): Promise<Contract> =>
      isUsingMockApi()
        ? mockDelay({ id, customer: 0, template: 0, status, external_envelope_id: "", created_at: "", updated_at: "", signed_at: null })
        : httpClient.post(`/contracts/${id}/transition/`, { status }),
  },

  subscriptions: {
    list: (): Promise<PaginatedResponse<Subscription>> =>
      isUsingMockApi() ? mockDelay(mockPage(mockSubscriptions)) : httpClient.get("/subscriptions/"),
    get: (id: number): Promise<Subscription> =>
      isUsingMockApi()
        ? mockDelay(mockSubscriptions.find((s) => s.id === id)!)
        : httpClient.get(`/subscriptions/${id}/`),
    entitlement: (id: number): Promise<Entitlement> =>
      isUsingMockApi()
        ? mockDelay({ entitled: true, status: "active", trial_end: null, current_period_end: null })
        : httpClient.get(`/subscriptions/${id}/entitlement/`),
  },

  payments: {
    list: (): Promise<PaginatedResponse<Payment>> =>
      isUsingMockApi() ? mockDelay(mockPage(mockPayments)) : httpClient.get("/payments/"),
    get: (id: number): Promise<Payment> =>
      isUsingMockApi()
        ? mockDelay(mockPayments.find((p) => p.id === id)!)
        : httpClient.get(`/payments/${id}/`),
    /** `POST /payments` — payment initiation for a subscription's next period; no trailing slash. */
    initiate: (subscriptionId: number): Promise<Payment> =>
      isUsingMockApi()
        ? mockDelay({
            id: Math.floor(Math.random() * 100000),
            subscription: subscriptionId,
            amount_pyg: 500000,
            status: "pending",
            gateway: "pagopar",
            gateway_order_id: "MOCK-ORDER",
            checkout_url: "https://pagopar.example.com/checkout/mock",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            confirmed_at: null,
          })
        : httpClient.post("/payments", { subscription: subscriptionId }),
    /** `POST /payments/{id}/refresh/` — poll the gateway for the order's current status. */
    refresh: (id: number): Promise<Payment> =>
      isUsingMockApi()
        ? paymentsApi.payments.get(id)
        : httpClient.post(`/payments/${id}/refresh/`),
  },
};
