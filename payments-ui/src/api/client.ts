import { USE_MOCK_API } from "./config";
import { httpClient } from "./httpClient";
import {
  mockApps,
  mockContractTemplates,
  mockCustomerDetails,
  mockCustomers,
  mockOverview,
  mockPayments,
  mockSubscriptions,
} from "../fixtures/data";
import type {
  ConsumingApp,
  ContractTemplate,
  Customer,
  CustomerDetail,
  OverviewSummary,
  Payment,
  Subscription,
} from "./types";

/** Small helper to keep mock responses feeling async without real network calls. */
function mockDelay<T>(value: T, ms = 150): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

/**
 * Typed client for the payments admin API.
 *
 * When `VITE_USE_MOCK_API` is not explicitly "false", every method resolves
 * against local fixture data instead of hitting a live backend — this lets
 * the UI run fully standalone while `payments/` is still being built.
 *
 * Endpoint paths are inferred (not yet confirmed against a published
 * OpenAPI schema) and namespaced under `/api/v1` to match the health check
 * route already present in `payments/config/urls.py`.
 */
export const paymentsApi = {
  overview: {
    get: (): Promise<OverviewSummary> =>
      USE_MOCK_API
        ? mockDelay(mockOverview)
        : httpClient.get<OverviewSummary>("/overview"),
  },

  subscriptions: {
    list: (): Promise<Subscription[]> =>
      USE_MOCK_API
        ? mockDelay(mockSubscriptions)
        : httpClient.get<Subscription[]>("/subscriptions"),
  },

  payments: {
    list: (): Promise<Payment[]> =>
      USE_MOCK_API
        ? mockDelay(mockPayments)
        : httpClient.get<Payment[]>("/payments"),
    get: (id: string): Promise<Payment | undefined> =>
      USE_MOCK_API
        ? mockDelay(mockPayments.find((p) => p.id === id))
        : httpClient.get<Payment>(`/payments/${id}`),
  },

  customers: {
    list: (): Promise<Customer[]> =>
      USE_MOCK_API
        ? mockDelay(mockCustomers)
        : httpClient.get<Customer[]>("/customers"),
    get: (id: string): Promise<CustomerDetail | undefined> =>
      USE_MOCK_API
        ? mockDelay(mockCustomerDetails[id])
        : httpClient.get<CustomerDetail>(`/customers/${id}`),
  },

  apps: {
    list: (): Promise<ConsumingApp[]> =>
      USE_MOCK_API
        ? mockDelay(mockApps)
        : httpClient.get<ConsumingApp[]>("/apps"),
    revoke: (id: string): Promise<void> =>
      USE_MOCK_API
        ? mockDelay(undefined)
        : httpClient.post<void>(`/apps/${id}/revoke`),
  },

  contractTemplates: {
    list: (): Promise<ContractTemplate[]> =>
      USE_MOCK_API
        ? mockDelay(mockContractTemplates)
        : httpClient.get<ContractTemplate[]>("/contract-templates"),
    update: (id: string, body: string): Promise<ContractTemplate> =>
      USE_MOCK_API
        ? mockDelay({ ...mockContractTemplates.find((t) => t.id === id)!, body })
        : httpClient.patch<ContractTemplate>(`/contract-templates/${id}`, { body }),
  },
};
