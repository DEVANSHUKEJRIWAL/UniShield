"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { isAuthenticated, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!ready) return;
    router.replace(isAuthenticated ? "/dashboard" : "/login");
  }, [ready, isAuthenticated, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="font-mono text-sm text-[var(--text-muted)]">Loading...</p>
    </div>
  );
}
