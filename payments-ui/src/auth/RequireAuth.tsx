import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { httpClient } from "../api/httpClient";
import { getStoredApiKey } from "../api/config";

/**
 * Route guard: an API key (machine mode) or a staff session grants access;
 * otherwise redirect to /login. Public routes (login, payment result) are
 * mounted outside this guard.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const hasApiKey = Boolean(getStoredApiKey());
  const me = useQuery({
    queryKey: ["auth-me"],
    queryFn: () => httpClient.get<{ username: string; is_staff: boolean }>("/auth/me"),
    enabled: !hasApiKey,
    retry: false,
    staleTime: 60_000,
  });

  if (hasApiKey) return <>{children}</>;
  if (me.isPending) return null;
  if (me.isError) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
