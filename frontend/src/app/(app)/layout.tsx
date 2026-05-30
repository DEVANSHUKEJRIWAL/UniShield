"use client";

import { AuthProvider } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
