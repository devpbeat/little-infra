export interface AdminProduct {
  slug: string;
  name: string;
  color: string;
  initial: string;
  live: boolean;
  tierCount: number;
  tierTotal: number;
  hasDemoCredentials: boolean;
}

/** Placeholder admin catalog data — real product management will come from an API in a later slice. */
export const adminProducts: AdminProduct[] = [
  { slug: "docuseal", name: "DocuSeal", color: "#3B82F6", initial: "D", live: true, tierCount: 3, tierTotal: 3, hasDemoCredentials: true },
  { slug: "payments", name: "Payments", color: "#FF5A1F", initial: "P", live: true, tierCount: 3, tierTotal: 3, hasDemoCredentials: true },
  { slug: "ara", name: "Ara", color: "#10B981", initial: "A", live: true, tierCount: 2, tierTotal: 2, hasDemoCredentials: false },
  { slug: "n8n", name: "n8n Automations", color: "#8B5CF6", initial: "N", live: true, tierCount: 3, tierTotal: 3, hasDemoCredentials: true },
  { slug: "plausible", name: "Plausible Analytics", color: "#6B7280", initial: "PL", live: false, tierCount: 0, tierTotal: 0, hasDemoCredentials: false },
];
