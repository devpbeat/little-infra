import { Link } from "react-router-dom";
import { Badge, Button, Card, ProgressBar, TabBar } from "../components/ui";
import { subscribedApps, tierBadgeTone } from "../data/subscriptions";

const TAB_ITEMS = [
  { label: "My apps", icon: "▦", active: true },
  { label: "Marketplace", icon: "🛒" },
  { label: "Billing", icon: "💳" },
  { label: "Account", icon: "👤" },
];

export function DashboardPage() {
  return (
    <div className="page dashboard-page">
      <header className="dashboard-header">
        <div className="container dashboard-header-inner">
          <div>
            <p className="dashboard-greeting">Good morning, 👋</p>
            <h1 className="dashboard-name">Maria</h1>
          </div>
          <div className="avatar-circle" aria-hidden="true">
            MR
          </div>
        </div>
      </header>

      <section className="dashboard-summary">
        <div className="container summary-tile-row">
          <Card className="summary-tile summary-tile-filled">
            <p className="summary-tile-value">3</p>
            <p className="summary-tile-label">Active apps</p>
          </Card>
          <Card className="summary-tile summary-tile-outlined">
            <p className="summary-tile-value">$65</p>
            <p className="summary-tile-label">Next bill · Oct 1</p>
          </Card>
        </div>
      </section>

      <section className="my-apps-section">
        <div className="container">
          <div className="marketplace-header">
            <h2>My apps</h2>
            {/* Stub for now — billing lands in a later slice. */}
            <a href="#" className="auth-link" onClick={() => console.log("TODO: manage billing")}>
              Manage billing
            </a>
          </div>
          <div className="app-list">
            {subscribedApps.map((app) => (
              <Card key={app.slug} className="app-card">
                <div className="app-card-top">
                  <div className="product-icon-tile app-icon-tile" style={{ background: app.color }}>
                    {app.initial}
                  </div>
                  <div className="app-card-info">
                    <div className="app-card-title-row">
                      <p className="product-name">{app.name}</p>
                      <Badge tone={tierBadgeTone[app.tier]}>{app.tier}</Badge>
                      <Badge tone="success">Active</Badge>
                    </div>
                    <p className="product-tagline">{app.usageLabel}</p>
                    <ProgressBar value={app.usagePercent} />
                  </div>
                </div>
                <Link to={`/products/${app.slug}`}>
                  <Button className="full-width">Open app</Button>
                </Link>
              </Card>
            ))}
          </div>

          <Card className="empty-hint-card">
            <p>Need another app? Your subscriptions will show up here.</p>
            <Link to="/">
              <Button variant="secondary">Browse marketplace</Button>
            </Link>
          </Card>
        </div>
      </section>

      <TabBar items={TAB_ITEMS} />
    </div>
  );
}
