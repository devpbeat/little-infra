import type { BadgeTone } from "../components/ui";

export interface SubscribedApp {
  slug: string;
  name: string;
  color: string;
  initial: string;
  tier: "Starter" | "Pro" | "Business";
  usageLabel: string;
  usagePercent: number;
}

/** Placeholder subscription data for the customer dashboard — real usage will come from an API later. */
export const subscribedApps: SubscribedApp[] = [
  {
    slug: "docuseal",
    name: "DocuSeal",
    color: "#3B82F6",
    initial: "D",
    tier: "Pro",
    usageLabel: "3 of 5 seats · 142 envelopes this month",
    usagePercent: 60,
  },
  {
    slug: "n8n",
    name: "n8n Automations",
    color: "#8B5CF6",
    initial: "N",
    tier: "Starter",
    usageLabel: "1 of 1 seats · 820 workflow runs this month",
    usagePercent: 82,
  },
  {
    slug: "payments",
    name: "Payments",
    color: "#FF5A1F",
    initial: "P",
    tier: "Business",
    usageLabel: "Unlimited seats · $12,480 processed this month",
    usagePercent: 40,
  },
];

export const tierBadgeTone: Record<SubscribedApp["tier"], BadgeTone> = {
  Starter: "neutral",
  Pro: "accent",
  Business: "accent",
};
