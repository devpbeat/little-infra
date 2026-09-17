import type { PropsWithChildren } from "react";
import { NavLink } from "react-router-dom";
import { ApiKeyBar } from "./ApiKeyBar";
import "./AppLayout.css";

const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/apps", label: "Apps & API Keys" },
  { to: "/customers", label: "Customers" },
  { to: "/contract-templates", label: "Contract Templates" },
];

export function AppLayout({ children }: PropsWithChildren) {
  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <div className="app-brand">
          Payments<span>Admin</span>
        </div>
        <nav className="app-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? "active" : undefined)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <ApiKeyBar />
      </aside>
      <main className="app-main">{children}</main>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions}
    </div>
  );
}
