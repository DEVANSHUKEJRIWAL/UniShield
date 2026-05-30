"use client";

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { setUnauthorizedHandler } from "@/lib/api";

interface AuthState {
  token: string | null;
  role: string | null;
  tenantId: string | null;
  email: string | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthState | null>(null);

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STORAGE = {
  token: "unishield_token",
  role: "unishield_role",
  tenant: "unishield_tenant",
  email: "unishield_email",
} as const;

function readStoredAuth() {
  if (typeof window === "undefined") {
    return { token: null, role: null, tenantId: null, email: null };
  }
  return {
    token: localStorage.getItem(STORAGE.token),
    role: localStorage.getItem(STORAGE.role),
    tenantId: localStorage.getItem(STORAGE.tenant),
    email: localStorage.getItem(STORAGE.email),
  };
}

function persistAuth(token: string, role: string, tenantId: string, email: string) {
  localStorage.setItem(STORAGE.token, token);
  localStorage.setItem(STORAGE.role, role);
  localStorage.setItem(STORAGE.tenant, tenantId);
  localStorage.setItem(STORAGE.email, email);
}

function clearStoredAuth() {
  localStorage.removeItem(STORAGE.token);
  localStorage.removeItem(STORAGE.role);
  localStorage.removeItem(STORAGE.tenant);
  localStorage.removeItem(STORAGE.email);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const router = useRouter();

  const logout = useCallback(() => {
    clearStoredAuth();
    setToken(null);
    setRole(null);
    setTenantId(null);
    setEmail(null);
    router.push("/login");
  }, [router]);

  useEffect(() => {
    const stored = readStoredAuth();
    setToken(stored.token);
    setRole(stored.role);
    setTenantId(stored.tenantId);
    setEmail(stored.email);
    setReady(true);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  const login = async (email: string, password: string) => {
    const res = await fetch(`${API}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error("Login failed");
    const data = await res.json();
    persistAuth(data.access_token, data.role, data.tenant_id, email);
    setToken(data.access_token);
    setRole(data.role);
    setTenantId(data.tenant_id);
    setEmail(email);
    router.push("/dashboard");
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        role,
        tenantId,
        email,
        ready,
        login,
        logout,
        isAuthenticated: !!token,
      }}
    >
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
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}
