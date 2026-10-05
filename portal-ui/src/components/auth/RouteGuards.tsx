import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { Show, useUser } from "@clerk/react";

/**
 * Requires an authenticated Clerk session. Unauthenticated visitors are
 * redirected to /login. Renders nothing while Clerk is still loading.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  return (
    <Show when="signed-in" fallback={<Navigate to="/login" replace />}>
      {children}
    </Show>
  );
}

/**
 * Requires an authenticated user flagged as staff via
 * `user.publicMetadata.staff === true` (set manually in the Clerk dashboard
 * on the user's "Public metadata" tab — see README for exact steps).
 * Non-staff (including signed-out visitors) are redirected to /dashboard,
 * which itself redirects signed-out visitors on to /login.
 */
export function RequireStaff({ children }: { children: ReactNode }) {
  const { user, isLoaded } = useUser();

  if (!isLoaded) {
    return null;
  }

  const isStaff = user?.publicMetadata?.staff === true;

  if (!isStaff) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}
