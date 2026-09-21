export interface Product {
  slug: string;
  name: string;
  tagline: string;
  /** Placeholder pricing — real plan data will come from an API in a later slice. */
  fromPriceUsd: number;
  color: string;
  initial: string;
}

export interface PricingTier {
  name: string;
  priceUsd: number;
  description: string;
  features: string[];
  highlighted?: boolean;
  badge?: string;
}

export interface DemoCredentials {
  url: string;
  username: string;
  password: string;
}

export interface ProductDetail extends Product {
  detailTagline: string;
  featureChips: string[];
  tiers: PricingTier[];
  demo: DemoCredentials;
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

/** Placeholder pricing, feature and demo-credential data for product detail pages. */
export const productDetails: Record<string, ProductDetail> = {
  docuseal: {
    ...products[0],
    detailTagline: "Send, sign and store documents securely — on your own domain, with your own branding.",
    featureChips: ["E-signatures", "Templates", "API"],
    tiers: [
      {
        name: "Starter",
        priceUsd: 12,
        description: "For freelancers getting started",
        features: ["Up to 50 envelopes/mo", "1 sender seat", "Email support"],
      },
      {
        name: "Pro",
        priceUsd: 29,
        description: "For growing teams that sign often",
        features: ["Unlimited envelopes", "5 sender seats", "Custom domain & branding", "Priority support"],
        highlighted: true,
        badge: "Most popular",
      },
      {
        name: "Business",
        priceUsd: 79,
        description: "For regulated businesses",
        features: ["Unlimited seats", "SSO & audit logs", "API & webhooks", "Dedicated instance"],
      },
    ],
    demo: {
      url: "demo.docuseal.ignite.app",
      username: "demo@ignite.app",
      password: "ignite-demo-2026",
    },
  },
};
