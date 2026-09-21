import { Link } from "react-router-dom";
import { Badge, Button, Card, FlameLogo } from "../components/ui";
import { products } from "../data/products";

const TRUST_ITEMS = ["99.9% uptime", "EU/US regions", "Daily backups"];

const FOOTER_COLUMNS: { title: string; links: string[] }[] = [
  { title: "Product", links: ["Marketplace", "Pricing", "Status"] },
  { title: "Company", links: ["About", "Blog", "Contact"] },
  { title: "Legal", links: ["Terms", "Privacy", "Security"] },
];

export function LandingPage() {
  return (
    <div className="page">
      <header className="topnav">
        <div className="container topnav-inner">
          <FlameLogo />
          <Link to="/login">
            <Button size="sm">Login</Button>
          </Link>
        </div>
      </header>

      <section className="hero">
        <div className="container">
          <Badge tone="accent">Self-hosted · Fully managed</Badge>
          <h1 className="hero-headline">Your business apps, hosted and ready.</h1>
          <p className="hero-subtitle">
            Open-source tools you own, running on infrastructure we manage. Pick an app, choose a plan, go
            live in minutes.
          </p>
          <div className="trust-row">
            {TRUST_ITEMS.map((item) => (
              <span key={item} className="trust-item">
                {item}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="marketplace">
        <div className="container">
          <div className="marketplace-header">
            <h2>Marketplace</h2>
            <span className="marketplace-count">{products.length} apps</span>
          </div>
          <div className="product-list">
            {products.map((product) => (
              <Card key={product.slug} className="product-card">
                <div className="product-icon-tile" style={{ background: product.color }}>
                  {product.initial}
                </div>
                <div className="product-info">
                  <p className="product-name">{product.name}</p>
                  <p className="product-tagline">{product.tagline}</p>
                  <p className="product-price">from ${product.fromPriceUsd}/mo</p>
                </div>
                <div className="product-actions">
                  {/* Stub for now — plan selection lands in a later slice. */}
                  <Button variant="secondary" size="sm" onClick={() => console.log("TODO: view plans", product.slug)}>
                    View plans
                  </Button>
                  {/* Stub for now — demo provisioning lands in a later slice. */}
                  <Button variant="ghost" size="sm" onClick={() => console.log("TODO: try demo", product.slug)}>
                    Try demo
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="container footer-inner">
          <p className="footer-brand">
            Managed hosting for the open-source apps your business runs on.
          </p>
          <div className="footer-columns">
            {FOOTER_COLUMNS.map((column) => (
              <div key={column.title}>
                <h4>{column.title}</h4>
                <ul>
                  {column.links.map((link) => (
                    <li key={link}>
                      <a href="#">{link}</a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
