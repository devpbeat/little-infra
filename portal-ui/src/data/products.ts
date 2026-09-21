export interface Product {
  slug: string;
  name: string;
  tagline: string;
  /** Placeholder pricing — real plan data will come from an API in a later slice. */
  fromPriceUsd: number;
  color: string;
  initial: string;
}

export const products: Product[] = [
  {
    slug: "docuseal",
    name: "DocuSeal",
    tagline: "Document signing",
    fromPriceUsd: 12,
    color: "#3B82F6",
    initial: "D",
  },
  {
    slug: "payments",
    name: "Payments",
    tagline: "Checkout & subscriptions",
    fromPriceUsd: 19,
    color: "#FF5A1F",
    initial: "P",
  },
  {
    slug: "ara",
    name: "Ara",
    tagline: "Customer platform",
    fromPriceUsd: 24,
    color: "#10B981",
    initial: "A",
  },
  {
    slug: "n8n",
    name: "n8n Automations",
    tagline: "Workflow automation",
    fromPriceUsd: 15,
    color: "#8B5CF6",
    initial: "N",
  },
];
