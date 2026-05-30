"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const fd = new FormData(e.currentTarget);
    try {
      await login(fd.get("email") as string, fd.get("password") as string);
    } catch {
      setError("Invalid credentials");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center obsidian-glow">
      <div className="obsidian-card w-full max-w-md">
        <h1 className="text-2xl font-bold"><span className="text-[var(--violet)]">Uni</span>Shield</h1>
        <p className="mt-2 text-[var(--text-secondary)]">Sign in to your SOC platform</p>
        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <input name="email" type="email" defaultValue="analyst@meridian.com" placeholder="Email" required className="w-full rounded border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-2 text-sm" />
          <input name="password" type="password" defaultValue="analyst123" placeholder="Password" required className="w-full rounded border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-2 text-sm" />
          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
          <button type="submit" disabled={loading} className="w-full rounded bg-[var(--violet)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50">
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
        <p className="mono mt-4 text-xs text-[var(--text-muted)]">Demo: analyst@meridian.com / analyst123</p>
      </div>
    </div>
  );
}
