import { useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Badge, Button, Card } from "../components/ui";
import { productDetails, type PricingTier, type ProductDetail } from "../data/products";

interface CheckoutLocationState {
  slug?: string;
  tierName?: string;
}

const FALLBACK_PRODUCT = productDetails.docuseal;
const FALLBACK_TIER = FALLBACK_PRODUCT.tiers[1]; // Pro

function resolveSelection(state: CheckoutLocationState | null): { product: ProductDetail; tier: PricingTier } {
  const product = (state?.slug && productDetails[state.slug]) || FALLBACK_PRODUCT;
  const tier = product.tiers.find((candidate) => candidate.name === state?.tierName) ?? product.tiers[1] ?? product.tiers[0];
  return { product, tier: tier ?? FALLBACK_TIER };
}

// Placeholder tax/yearly math — a real checkout will get these from the Payments API.
const TAX_ESTIMATE = 2.61;
const YEARLY_DISCOUNT_MONTHS_FREE = 2;

type BillingCycle = "monthly" | "yearly";

export function CheckoutPage() {
  const location = useLocation();
  const { product, tier } = useMemo(
    () => resolveSelection(location.state as CheckoutLocationState | null),
    [location.state],
  );
  const monthlyPrice = tier.priceUsd;
  const yearlyPrice = Math.round(monthlyPrice * 12 * ((12 - YEARLY_DISCOUNT_MONTHS_FREE) / 12));
  const totalDueToday = monthlyPrice + TAX_ESTIMATE;
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("monthly");

  return (
    <div className="page checkout-page">
      <header className="topnav">
        <div className="container topnav-inner">
          <Link to={`/products/${product.slug}`} className="icon-button" aria-label="Back">
            ←
          </Link>
          <span className="topnav-title">Checkout</span>
          <span className="step-counter">2/2</span>
        </div>
      </header>

      <section className="checkout-intro">
        <div className="container">
          <h1 className="checkout-heading">Subscribe to {product.name}</h1>
          <p className="checkout-subheading">Review your plan and add a payment method.</p>
        </div>
      </section>

      <section className="checkout-section">
        <div className="container checkout-stack">
          <Card className="order-summary-card">
            <div className="order-summary-header">
              <div className="product-icon-tile app-icon-tile" style={{ background: product.color }}>
                {product.initial}
              </div>
              <Badge tone="accent">{tier.name}</Badge>
            </div>

            <div className="billing-cycle-row">
              <span className="billing-cycle-label">BILLING CYCLE</span>
              <div className="billing-cycle-toggle">
                <button
                  type="button"
                  className={billingCycle === "monthly" ? "active" : ""}
                  onClick={() => setBillingCycle("monthly")}
                >
                  Monthly
                </button>
                <button
                  type="button"
                  className={billingCycle === "yearly" ? "active" : ""}
                  onClick={() => setBillingCycle("yearly")}
                >
                  Yearly
                  <Badge tone="success" className="save-badge">
                    Save 20%
                  </Badge>
                </button>
              </div>
              {billingCycle === "yearly" && (
                <p className="yearly-hint">${yearlyPrice}/yr — that's {YEARLY_DISCOUNT_MONTHS_FREE}+ months free</p>
              )}
            </div>

            <div className="order-breakdown">
              <div className="order-breakdown-row">
                <span>Subtotal · {tier.name}, monthly</span>
                <span>${monthlyPrice.toFixed(2)}</span>
              </div>
              <div className="order-breakdown-row">
                <span>Tax (est.)</span>
                <span>${TAX_ESTIMATE.toFixed(2)}</span>
              </div>
              <div className="order-breakdown-row order-breakdown-total">
                <span>Total due today</span>
                <span>${totalDueToday.toFixed(2)}/mo</span>
              </div>
            </div>
          </Card>

          <Card className="payment-card">
            <p className="payment-card-title">Payment method</p>
            <div className="card-brand-row">
              <span className="card-brand-chip">VISA</span>
              <span className="card-brand-chip">MC</span>
              <span className="card-brand-chip">AMEX</span>
            </div>

            <div className="form-field">
              <label className="form-label" htmlFor="card-number">
                Card number
              </label>
              <input
                id="card-number"
                className="text-input mono"
                type="text"
                inputMode="numeric"
                defaultValue="4242 4242 4242 4242"
                readOnly
              />
            </div>

            <div className="payment-field-row">
              <div className="form-field">
                <label className="form-label" htmlFor="card-expiry">
                  Expiry (MM/YY)
                </label>
                <input id="card-expiry" className="text-input mono" type="text" placeholder="MM/YY" />
              </div>
              <div className="form-field">
                <label className="form-label" htmlFor="card-cvc">
                  CVC
                </label>
                <input id="card-cvc" className="text-input mono" type="text" placeholder="CVC" />
              </div>
            </div>

            <div className="form-field">
              <label className="form-label" htmlFor="card-name">
                Cardholder name
              </label>
              <input id="card-name" className="text-input" type="text" placeholder="Full name on card" />
            </div>

            <p className="integration-note">
              Integration point: Card fields are rendered by the existing Payments service (hosted
              fields + tokenization). No card data touches this app. POST /payments/subscriptions
            </p>
          </Card>

          {/* Stub for now — subscription creation lands once the Payments API is wired up. */}
          <Button
            className="full-width"
            onClick={() => console.log("TODO: subscribe & provision — Payments API integration pending")}
          >
            Subscribe & provision · ${totalDueToday.toFixed(2)}
          </Button>

          <p className="tenant-provision-pill mono">
            Your tenant will be set up automatically at {product.slug}.store.ignitesolutions.click
          </p>

          <p className="secure-payment-line">Secure 256-bit TLS payment · Cancel anytime</p>
        </div>
      </section>
    </div>
  );
}
