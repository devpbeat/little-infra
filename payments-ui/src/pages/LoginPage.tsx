import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Button, Card } from "../components/ui";
import { httpClient, ApiError } from "../api/httpClient";

export function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const login = useMutation({
    mutationFn: () =>
      httpClient.post<{ username: string; is_staff: boolean }>("/auth/login", {
        username,
        password,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth-me"] });
      navigate("/");
    },
  });

  return (
    <div style={{ maxWidth: 380, margin: "12vh auto" }}>
      <Card>
        <h2 style={{ marginTop: 0 }}>Admin login</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            login.mutate();
          }}
          style={{ display: "flex", flexDirection: "column", gap: 14 }}
        >
          <label>
            <div className="stat-card-label">Username</div>
            <input
              className="text-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </label>
          <label>
            <div className="stat-card-label">Password</div>
            <input
              className="text-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </label>
          {login.isError && (
            <p style={{ color: "var(--danger, #f87171)", fontSize: 13 }}>
              {login.error instanceof ApiError ? login.error.message : "Login failed."}
            </p>
          )}
          <Button type="submit" disabled={login.isPending}>
            {login.isPending ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <p style={{ color: "var(--text-dim)", fontSize: 12, marginBottom: 0 }}>
          Staff accounts only. Machine integrations use an API key instead.
        </p>
      </Card>
    </div>
  );
}
