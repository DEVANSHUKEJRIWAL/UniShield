import Link from "next/link";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/agents", label: "Agents" },
  { href: "/alerts", label: "Alerts" },
  { href: "/compliance", label: "Compliance" },
  { href: "/reporting", label: "Reporting" },
  { href: "/network", label: "Network" },
  { href: "/cloud", label: "Cloud" },
];

export function Sidebar() {
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
          {NAV_ITEMS.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className="block rounded-md px-3 py-2 text-sm text-[var(--text-secondary)] transition hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)]"
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <div className="border-t border-[var(--border)] p-4">
        <p className="mono text-xs text-[var(--text-muted)]">Tenant: meridian-financial</p>
      </div>
    </aside>
  );
}
