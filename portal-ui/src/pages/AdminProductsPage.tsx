import { useState } from "react";
import { Badge, Button, Card, Toggle } from "../components/ui";
import { adminProducts as initialAdminProducts, type AdminProduct } from "../data/adminProducts";

export function AdminProductsPage() {
  const [adminProducts, setAdminProducts] = useState<AdminProduct[]>(initialAdminProducts);
  const liveCount = adminProducts.filter((product) => product.live).length;

  const toggleLive = (slug: string) => {
    setAdminProducts((current) =>
      current.map((product) => (product.slug === slug ? { ...product, live: !product.live } : product)),
    );
  };

  return (
    <div className="page admin-page">
      <header className="admin-header">
        <div className="container admin-header-inner">
          <Badge tone="neutral">Admin panel</Badge>
          {/* Stub for now — the admin nav menu lands in a later slice. */}
          <button type="button" className="icon-button" aria-label="Menu" onClick={() => console.log("TODO: open admin menu")}>
            ☰
          </button>
        </div>
      </header>

      <section className="admin-products-section">
        <div className="container">
          <h1 className="admin-title">Products</h1>
          <p className="admin-subtitle">
            {adminProducts.length} products · {liveCount} live in the marketplace
          </p>

          {/* Stub for now — product creation lands in a later slice. */}
          <Button className="full-width" onClick={() => console.log("TODO: add product")}>
            Add product
          </Button>

          <div className="admin-search-row">
            <input className="text-input admin-search-input" type="search" placeholder="Search products" />
            {/* Stub for now — filtering lands in a later slice. */}
            <button type="button" className="icon-button admin-filter-button" aria-label="Filter" onClick={() => console.log("TODO: open filters")}>
              ⚙
            </button>
          </div>

          <div className="admin-product-list">
            {adminProducts.map((product) => (
              <Card key={product.slug} className="admin-product-card">
                <div className="admin-product-top">
                  <div className="product-icon-tile app-icon-tile" style={{ background: product.color }}>
                    {product.initial}
                  </div>
                  <div className="admin-product-info">
                    <p className="product-name">{product.name}</p>
                    <Badge tone={product.live ? "success" : "neutral"}>{product.live ? "Live" : "Draft · hidden"}</Badge>
                  </div>
                  <Toggle
                    checked={product.live}
                    onChange={() => toggleLive(product.slug)}
                    label={`Toggle ${product.name} live status`}
                  />
                </div>
                <div className="admin-product-meta">
                  <span className="admin-meta-item">
                    <span className="admin-meta-label">TIERS</span> {product.tierCount}/{product.tierTotal}
                  </span>
                  <span className="admin-meta-item">
                    <span className="admin-meta-label">DEMO CREDS</span>{" "}
                    {product.hasDemoCredentials ? (
                      <span className="admin-meta-yes">✓ Yes</span>
                    ) : (
                      <span className="admin-meta-no">✕ No</span>
                    )}
                  </span>
                </div>
                {/* Stub for now — product editing lands in a later slice. */}
                <Button variant="secondary" className="full-width" onClick={() => console.log("TODO: edit product", product.slug)}>
                  Edit
                </Button>
              </Card>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
