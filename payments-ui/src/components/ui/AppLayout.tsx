import type { PropsWithChildren } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiKeyBar } from "./ApiKeyBar";
import { httpClient } from "../../api/httpClient";
import { getStoredApiKey } from "../../api/config";
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
        <SessionBar />
      </aside>
      <main className="app-main">{children}</main>
    </div>
  );
}

function SessionBar() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const hasApiKey = Boolean(getStoredApiKey());
  const me = useQuery({
    queryKey: ["auth-me"],
    queryFn: () => httpClient.get<{ username: string; is_staff: boolean }>("/auth/me"),
    enabled: !hasApiKey,
    retry: false,
    staleTime: 60_000,
  });

  if (hasApiKey || !me.data) return null;
  return (
    <div style={{ padding: "8px 12px", fontSize: 12, color: "var(--text-dim)" }}>
      <span>{me.data.username}</span>
      <button
        type="button"
        style={{ marginLeft: 8 }}
        onClick={async () => {
          await httpClient.post("/auth/logout");
          queryClient.removeQueries({ queryKey: ["auth-me"] });
          navigate("/login");
        }}
      >
        Log out
      </button>
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
