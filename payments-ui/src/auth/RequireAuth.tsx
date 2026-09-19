import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";
import { httpClient } from "../api/httpClient";
import { getStoredApiKey, setSessionAuthenticated } from "../api/config";

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

  // Record the session outcome synchronously so data queries in the child
  // tree (which mount after this render) resolve mock-vs-real correctly.
  // Children's effects fire after this render body runs, so the flag is
  // already set by the time `isUsingMockApi()` is consulted.
  if (me.isSuccess) setSessionAuthenticated(true);
  else if (me.isError) setSessionAuthenticated(false);

  if (hasApiKey) return <>{children}</>;
  if (me.isPending) return null;
  if (me.isError) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
