"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, Suspense } from "react";
import { Shield } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { ThemeToggle } from "@/components/ThemeToggle";

function LoginForm() {
  const { login, isAuthenticated, ready } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (ready && isAuthenticated) {
      const next = searchParams.get("next") || "/dashboard";
      router.replace(next);
    }
  }, [ready, isAuthenticated, router, searchParams]);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");
    const fd = new FormData(e.currentTarget);
    try {
      await login(fd.get("email") as string, fd.get("password") as string);
    } catch {
      setError("Invalid credentials — ensure ./scripts/dev-local.sh is running");
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <div className="admin-center flex min-h-screen items-center justify-center">
        <p className="t-muted mono">Loading…</p>
      </div>
    );
  }

  return (
    <div className="admin-center flex min-h-screen items-center justify-center p-6">
      <div className="absolute right-6 top-6 z-50">
        <ThemeToggle />
      </div>

      <div className="card" style={{ width: "100%", maxWidth: 420, padding: "32px 28px" }}>
        <div
          className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl"
          style={{ background: "var(--purple-deep)", boxShadow: "var(--shadow-soft)" }}
        >
          <Shield size={26} className="text-white" />
        </div>

        <h1 className="t-title" style={{ textAlign: "center", fontSize: 24 }}>
          UniShield
        </h1>
        <p className="t-muted mono" style={{ textAlign: "center", fontSize: 11, marginTop: 4 }}>
          Admin Center · AI-native cyber defense
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <input
            name="email"
            type="email"
            defaultValue="analyst@meridian.com"
            required
            placeholder="Email"
            className="ac-form-control"
            style={{ width: "100%", borderRadius: 12 }}
          />
          <input
            name="password"
            type="password"
            defaultValue="analyst123"
            required
            placeholder="Password"
            className="ac-form-control"
            style={{ width: "100%", borderRadius: 12 }}
          />
          {error ? <p style={{ textAlign: "center", fontSize: 13, color: "var(--r-sec2)" }}>{error}</p> : null}
          <button type="submit" disabled={loading} className="btn-accent" style={{ width: "100%" }}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="t-muted mono" style={{ textAlign: "center", fontSize: 10, marginTop: 20 }}>
          analyst@meridian.com / analyst123
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="admin-center flex min-h-screen items-center justify-center">
          <p className="t-muted mono">Loading…</p>
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
