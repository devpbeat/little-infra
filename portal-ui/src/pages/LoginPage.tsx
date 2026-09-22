import { useState } from "react";
import { Button, Card, FlameLogo } from "../components/ui";

type AuthMode = "login" | "signup";

export function LoginPage() {
  const [mode, setMode] = useState<AuthMode>("login");

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <FlameLogo />
          <h1>Welcome back 👋</h1>
          <p>Log in to manage your apps, subscriptions and tenants.</p>
        </div>

        <Card>
          <div className="auth-toggle">
            <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
              Log in
            </button>
            <button
              type="button"
              className={mode === "signup" ? "active" : ""}
              onClick={() => setMode("signup")}
            >
              Create account
            </button>
          </div>

          {mode === "login" ? <LoginForm /> : <SignupForm />}
        </Card>
      </div>
    </div>
  );
}

function LoginForm() {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        // TODO: wire real authentication once Clerk (Organizations) is integrated.
        console.log("TODO: submit login — Clerk integration pending");
      }}
    >
      <div className="form-field">
        <label className="form-label" htmlFor="login-email">
          Email
        </label>
        <input id="login-email" className="text-input" type="email" autoComplete="email" required />
      </div>

      <div className="form-field">
        <label className="form-label" htmlFor="login-password">
          Password
        </label>
        <div className="password-field">
          <input
            id="login-password"
            className="text-input"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            required
          />
          <button
            type="button"
            className="password-toggle"
            onClick={() => setShowPassword((value) => !value)}
          >
            {showPassword ? "Hide" : "Show"}
          </button>
        </div>
      </div>

      <div className="auth-row-between">
        <label className="auth-checkbox">
          <input type="checkbox" />
          Keep me logged in
        </label>
        <a className="auth-link" href="#">
          Forgot password?
        </a>
      </div>

      <Button type="submit" className="full-width">
        Log in
      </Button>

      <div className="auth-divider">or</div>

      <Button
        type="button"
        variant="secondary"
        className="full-width"
        onClick={() => console.log("TODO: continue with Google — Clerk integration pending")}
      >
        Continue with Google
      </Button>
    </form>
  );
}

function SignupForm() {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        // TODO: wire real account creation once Clerk (Organizations) is integrated.
        console.log("TODO: submit sign up — Clerk integration pending");
      }}
    >
      <div className="form-field">
        <label className="form-label" htmlFor="signup-name">
          Full name
        </label>
        <input id="signup-name" className="text-input" type="text" autoComplete="name" required />
      </div>

      <div className="form-field">
        <label className="form-label" htmlFor="signup-email">
          Email
        </label>
        <input id="signup-email" className="text-input" type="email" autoComplete="email" required />
      </div>

      <div className="form-field">
        <label className="form-label" htmlFor="signup-password">
          Password
        </label>
        <input
          id="signup-password"
          className="text-input"
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
        />
      </div>

      <p className="auth-terms">By creating an account, you agree to our Terms and Privacy Policy.</p>

      <Button type="submit" className="full-width">
        Create account
      </Button>
    </form>
  );
}
