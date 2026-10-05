import { SignUp } from "@clerk/react";
import { FlameLogo } from "../components/ui";
import { clerkAppearance } from "../lib/clerkAppearance";

export function SignupPage() {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <FlameLogo />
          <h1>Create your account</h1>
          <p>Set up access to manage your apps, subscriptions and tenants.</p>
        </div>

        <SignUp routing="path" path="/signup" signInUrl="/login" appearance={clerkAppearance} />
      </div>
    </div>
  );
}
