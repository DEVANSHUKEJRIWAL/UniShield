"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", roles: ["*"] },
  { href: "/dashboard/executive", label: "Executive", roles: ["CISO", "READONLY_BOARD", "PLATFORM_ADMIN", "CLIENT_ADMIN"] },
  { href: "/agents", label: "Agents", roles: ["*"] },
  { href: "/alerts", label: "Alerts", roles: ["SOC_ANALYST", "CISO", "CLIENT_ADMIN", "PLATFORM_ADMIN"] },
  { href: "/investigation", label: "Investigation", roles: ["SOC_ANALYST", "CISO", "PLATFORM_ADMIN"] },
  { href: "/compliance", label: "Compliance", roles: ["GRC", "CISO", "PLATFORM_ADMIN"] },
  { href: "/reporting", label: "Reporting", roles: ["GRC", "CISO", "READONLY_BOARD", "PLATFORM_ADMIN"] },
  { href: "/network", label: "Network", roles: ["SOC_ANALYST", "CISO", "PLATFORM_ADMIN"] },
  { href: "/cloud", label: "Cloud", roles: ["SOC_ANALYST", "CISO", "PLATFORM_ADMIN"] },
  { href: "/clients", label: "Clients", roles: ["PLATFORM_ADMIN"] },
  { href: "/settings", label: "Settings", roles: ["*"] },
];

export function Sidebar() {
  const pathname = usePathname();
  const { tenantId, role, email, logout } = useAuth();

  const visible = NAV_ITEMS.filter(
    (item) => item.roles.includes("*") || (role && item.roles.includes(role))
  );

  return (
    <aside className="flex w-64 flex-col border-r border-[var(--border)] bg-[var(--bg-elevated)]">
      <div className="border-b border-[var(--border)] p-6">
        <h1 className="text-xl font-bold tracking-tight">
          <span className="text-[var(--violet)]">Uni</span>Shield
        </h1>
        <p className="mono mt-1 text-xs text-[var(--text-muted)]">Obsidian SOC Platform</p>
      </div>
      <nav className="flex-1 p-4">
        <ul className="space-y-1">
          {visible.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`block rounded-md px-3 py-2 text-sm transition ${
                  pathname === item.href || pathname.startsWith(item.href + "/")
                    ? "bg-[var(--violet)]/20 text-[var(--text-primary)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)]"
                }`}
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <div className="border-t border-[var(--border)] p-4">
        <p className="mono text-xs text-[var(--text-muted)]">Tenant: {tenantId}</p>
        <p className="mono text-xs text-[var(--text-secondary)]">{email}</p>
        <button onClick={logout} className="mono mt-2 text-xs text-[var(--danger)] hover:underline">
          Sign out
        </button>
      </div>
    </aside>
  );
}
