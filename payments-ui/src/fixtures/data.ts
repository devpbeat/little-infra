import type {
  ConsumingApp,
  ContractTemplate,
  Customer,
  CustomerDetail,
  OverviewSummary,
  Payment,
  Subscription,
} from "../api/types";

export const mockOverview: OverviewSummary = {
  activeSubscriptions: 128,
  trialsEndingSoon: 9,
  mrrCents: 1_432_000,
  paymentsLast30d: 312,
  paymentSuccessRate: 0.984,
};

export const mockSubscriptions: Subscription[] = [
  {
    id: "sub_1",
    customerId: "cus_acme",
    customerName: "Acme Corp",
    planName: "SaaS Monthly",
    status: "active",
    renewalDate: "2026-10-01",
    mrrCents: 14900,
  },
  {
    id: "sub_2",
    customerId: "cus_nordic",
    customerName: "Nordic Labs",
    planName: "SaaS Annual",
    status: "active",
    renewalDate: "2027-01-14",
    mrrCents: 9900,
  },
  {
    id: "sub_3",
    customerId: "cus_vera",
    customerName: "Vera Studio",
    planName: "SaaS Monthly",
    status: "trial",
    renewalDate: "2026-09-22",
    mrrCents: 0,
  },
  {
    id: "sub_4",
    customerId: "cus_blue",
    customerName: "Blue Harbor",
    planName: "SaaS Monthly",
    status: "past_due",
    renewalDate: "2026-09-12",
    mrrCents: 19900,
  },
];

export const mockPayments: Payment[] = [
  {
    id: "PAY-20894",
    customerId: "cus_acme",
    customerName: "Acme Corp",
    amountCents: 14900,
    currency: "USD",
    method: "Pagopar",
    status: "succeeded",
    gatewayRef: "pgp_9f2ac3",
    invoiceRef: "INV-2026-0915",
    subscriptionPlan: "SaaS Monthly",
    qrPayload: "https://pagopar.com/pay/pgp_9f2ac3",
    createdAt: "2026-09-15T14:22:00Z",
  },
  {
    id: "PAY-20871",
    customerId: "cus_nordic",
    customerName: "Nordic Labs",
    amountCents: 9900,
    currency: "USD",
    method: "Pagopar",
    status: "succeeded",
    gatewayRef: "pgp_7a11bd",
    invoiceRef: "INV-2026-0914",
    subscriptionPlan: "SaaS Annual",
    createdAt: "2026-09-14T09:03:00Z",
  },
  {
    id: "PAY-20855",
    customerId: "cus_blue",
    customerName: "Blue Harbor",
    amountCents: 19900,
    currency: "USD",
    method: "Pagopar",
    status: "failed",
    gatewayRef: "pgp_44f0e2",
    invoiceRef: "INV-2026-0913",
    subscriptionPlan: "SaaS Monthly",
    createdAt: "2026-09-13T18:40:00Z",
  },
  {
    id: "PAY-20812",
    customerId: "cus_kilo",
    customerName: "Kilo Systems",
    amountCents: 450000,
    currency: "USD",
    method: "Pagopar",
    status: "pending",
    gatewayRef: "pgp_a02c19",
    invoiceRef: "INV-2026-0911",
    createdAt: "2026-09-11T11:15:00Z",
  },
];

export const mockCustomers: Customer[] = [
  {
    id: "cus_acme",
    name: "Acme Corp",
    email: "billing@acme.example.com",
    createdAt: "2026-03-02",
    dealType: "saas_monthly",
    contractStatus: "signed",
    subscriptionStatus: "active",
    lifetimePaidCents: 178900,
  },
  {
    id: "cus_nordic",
    name: "Nordic Labs",
    email: "ops@nordiclabs.example.com",
    createdAt: "2026-01-10",
    dealType: "saas_annual",
    contractStatus: "signed",
    subscriptionStatus: "active",
    lifetimePaidCents: 9900,
  },
  {
    id: "cus_vera",
    name: "Vera Studio",
    email: "hello@vera.example.com",
    createdAt: "2026-09-08",
    dealType: "saas_monthly",
    contractStatus: "sent",
    subscriptionStatus: "trial",
    lifetimePaidCents: 0,
  },
  {
    id: "cus_kilo",
    name: "Kilo Systems",
    email: "finance@kilosystems.example.com",
    createdAt: "2026-08-01",
    dealType: "fixed_with_ownership",
    contractStatus: "signed",
    subscriptionStatus: null,
    lifetimePaidCents: 450000,
  },
  {
    id: "cus_blue",
    name: "Blue Harbor",
    email: "accounts@blueharbor.example.com",
    createdAt: "2025-12-15",
    dealType: "fixed_no_ownership_hosting",
    contractStatus: "signed",
    subscriptionStatus: "past_due",
    lifetimePaidCents: 238800,
  },
];

export const mockCustomerDetails: Record<string, CustomerDetail> = Object.fromEntries(
  mockCustomers.map((customer) => [
    customer.id,
    {
      ...customer,
      timeline: [
        { id: "t1", date: "2026-03-02", title: "Contract sent for signature", kind: "contract" },
        { id: "t2", date: "2026-03-03", title: "Contract signed (DocuSign)", kind: "contract" },
        { id: "t3", date: "2026-03-05", title: "Subscription activated", kind: "subscription" },
        { id: "t4", date: "2026-09-01", title: "Payment succeeded — $149.00", kind: "payment" },
      ],
      payments: mockPayments.filter((p) => p.customerId === customer.id),
    } satisfies CustomerDetail,
  ]),
);

export const mockApps: ConsumingApp[] = [
  {
    id: "app_1",
    name: "ara-frontend",
    environment: "production",
    apiKeyMasked: "pk_live_••••3f2a",
    createdAt: "2026-03-02",
    lastUsedAt: "2026-09-16T10:58:00Z",
    status: "active",
  },
  {
    id: "app_2",
    name: "ara-frontend",
    environment: "staging",
    apiKeyMasked: "pk_test_••••88ce",
    createdAt: "2026-03-02",
    lastUsedAt: "2026-09-15T21:10:00Z",
    status: "active",
  },
  {
    id: "app_3",
    name: "internal-cli",
    environment: "production",
    apiKeyMasked: "pk_live_••••11de",
    createdAt: "2025-11-19",
    lastUsedAt: "2026-08-13T08:02:00Z",
    status: "disabled",
  },
];

export const mockContractTemplates: ContractTemplate[] = [
  {
    id: "tpl_saas_monthly",
    dealType: "saas_monthly",
    name: "SaaS — Monthly",
    description: "Recurring monthly subscription billing, no code ownership transfer.",
    body:
      'This Agreement is entered into by {{company_name}} ("Provider") and {{customer_name}} ("Client") on {{contract_date}}.\n\nPlan: {{plan_name}}\nBilling: {{billing_amount}} / month\n\nThe Client is granted a non-exclusive license to use the Service. No source code or intellectual property is transferred under this plan.',
    updatedAt: "2026-06-01",
  },
  {
    id: "tpl_saas_annual",
    dealType: "saas_annual",
    name: "SaaS — Annual",
    description: "Recurring annual subscription billing, no code ownership transfer.",
    body:
      'This Agreement is entered into by {{company_name}} ("Provider") and {{customer_name}} ("Client") on {{contract_date}}.\n\nPlan: {{plan_name}}\nBilling: {{billing_amount}} / year\n\nThe Client is granted a non-exclusive license to use the Service for the contract term. No source code or intellectual property is transferred under this plan.',
    updatedAt: "2026-06-01",
  },
  {
    id: "tpl_fixed_ownership",
    dealType: "fixed_with_ownership",
    name: "Fixed Price — With Code Ownership",
    description: "One-time payment, IP transferred to client on completion.",
    body:
      'This Agreement is entered into by {{company_name}} ("Provider") and {{customer_name}} ("Client") on {{contract_date}}.\n\nScope: {{project_scope}}\nFee: {{total_fee}} (fixed)\n\nUpon final payment, all source code and intellectual property developed under this Agreement transfer to the Client.',
    updatedAt: "2026-05-20",
  },
  {
    id: "tpl_fixed_no_ownership_hosting",
    dealType: "fixed_no_ownership_hosting",
    name: "Fixed Price — No Ownership + Hosting",
    description: "One-time build fee plus recurring hosting; IP retained by Provider.",
    body:
      'This Agreement is entered into by {{company_name}} ("Provider") and {{customer_name}} ("Client") on {{contract_date}}.\n\nScope: {{project_scope}}\nBuild fee: {{total_fee}} (fixed)\nHosting: {{hosting_fee}} / month\n\nThe Provider retains all source code and intellectual property. The Client is granted a right to use the hosted Service while hosting fees are current.',
    updatedAt: "2026-05-20",
  },
];
