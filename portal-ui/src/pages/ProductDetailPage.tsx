import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge, Button, Card } from "../components/ui";
import { productDetails } from "../data/products";

export function ProductDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const product = slug ? productDetails[slug] : undefined;

  if (!product) {
    return (
      <div className="page">
        <div className="container detail-not-found">
          <p>Product not found.</p>
          <Link to="/">
            <Button variant="secondary">Back to marketplace</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="topnav">
        <div className="container topnav-inner">
          <Link to="/" className="icon-button" aria-label="Back to marketplace">
            ←
          </Link>
          <span className="topnav-title">Marketplace</span>
          {/* Stub for now — sharing lands in a later slice. */}
          <button
            type="button"
            className="icon-button"
            aria-label="Share"
            onClick={() => console.log("TODO: share product", product.slug)}
          >
            ⤴
          </button>
        </div>
      </header>

      <section className="detail-hero">
        <div className="container">
          <div className="product-icon-tile detail-icon-tile" style={{ background: product.color }}>
            {product.initial}
          </div>
          <h1 className="detail-name">{product.name}</h1>
          <p className="detail-tagline">{product.detailTagline}</p>
          <div className="chip-row">
            {product.featureChips.map((chip) => (
              <span key={chip} className="feature-chip">
                {chip}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="pricing-section">
        <div className="container">
          <h2>Choose a plan</h2>
          <div className="tier-list">
            {product.tiers.map((tier) => (
              <Card key={tier.name} className={["tier-card", tier.highlighted ? "tier-card-highlighted" : ""].join(" ")}>
                {tier.badge && (
                  <Badge tone="accent" className="tier-badge">
                    {tier.badge}
                  </Badge>
                )}
                <div className="tier-header">
                  <h3>{tier.name}</h3>
                  <p className="tier-price">
                    ${tier.priceUsd}
                    <span className="tier-price-period">/mo</span>
                  </p>
                </div>
                <p className="tier-description">{tier.description}</p>
                <ul className="tier-feature-list">
                  {tier.features.map((feature) => (
                    <li key={feature}>{feature}</li>
                  ))}
                </ul>
                <Link to="/checkout">
                  <Button variant={tier.highlighted ? "primary" : "secondary"} className="full-width">
                    Subscribe to {tier.name}
                  </Button>
                </Link>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="demo-section">
        <div className="container">
          <Card className="demo-card">
            <p className="demo-eyebrow">Live sandbox · resets every 24h</p>
            <h2 className="demo-heading">Try the demo</h2>
            <div className="demo-credentials">
              <CredentialRow label="DEMO URL" value={product.demo.url} />
              <CredentialRow label="USERNAME" value={product.demo.username} />
              <CredentialRow label="PASSWORD" value={product.demo.password} />
            </div>
            <a
              className="full-width"
              href={`https://${product.demo.url}`}
              target="_blank"
              rel="noreferrer"
            >
              <Button className="full-width">Open live demo</Button>
            </a>
          </Card>
        </div>
      </section>
    </div>
  );
}

function CredentialRow({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API may be unavailable (e.g. insecure context) — fail silently.
    }
  };

  return (
    <div className="credential-row">
      <span className="credential-label">{label}</span>
      <span className="credential-value mono">{value}</span>
      <button type="button" className="icon-button" aria-label={`Copy ${label.toLowerCase()}`} onClick={handleCopy}>
        {copied ? "✓" : "⧉"}
      </button>
    </div>
  );
}
