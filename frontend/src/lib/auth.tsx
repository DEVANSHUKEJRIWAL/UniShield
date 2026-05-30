"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";

interface AuthState {
  token: string | null;
  role: string | null;
  tenantId: string | null;
  email: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthState | null>(null);

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const t = localStorage.getItem("unishield_token");
    const r = localStorage.getItem("unishield_role");
    const tid = localStorage.getItem("unishield_tenant");
    const e = localStorage.getItem("unishield_email");
    if (t) { setToken(t); setRole(r); setTenantId(tid); setEmail(e); }
  }, []);

  const login = async (email: string, password: string) => {
    const res = await fetch(`${API}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error("Login failed");
    const data = await res.json();
    localStorage.setItem("unishield_token", data.access_token);
    localStorage.setItem("unishield_role", data.role);
    localStorage.setItem("unishield_tenant", data.tenant_id);
    localStorage.setItem("unishield_email", email);
    setToken(data.access_token);
    setRole(data.role);
    setTenantId(data.tenant_id);
    setEmail(email);
    router.push("/dashboard");
  };

  const logout = () => {
    localStorage.clear();
    setToken(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ token, role, tenantId, email, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function authHeaders(token: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}
