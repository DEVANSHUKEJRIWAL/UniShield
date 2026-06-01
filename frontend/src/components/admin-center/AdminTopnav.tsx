"use client";

import { useEffect, useState } from "react";
import { Bell, Bot, Settings, Sun, Moon } from "lucide-react";
import { useAuth } from "@/lib/auth";
import Link from "next/link";

type Props = { hitlCount?: number };

export function AdminTopnav({ hitlCount = 0 }: Props) {
  const { email, logout } = useAuth();
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const initials = email?.slice(0, 2).toUpperCase() ?? "US";

  useEffect(() => {
    const t = document.documentElement.getAttribute("data-theme");
    setTheme(t === "light" ? "light" : "dark");
  }, []);

  const setThemeMode = (mode: "light" | "dark") => {
    setTheme(mode);
    document.documentElement.setAttribute("data-theme", mode);
    localStorage.setItem("unishield-theme", mode);
  };

  return (
    <header className="topnav">
      <div className="status-live">
        <span className="pulse-dot" style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--m3)", display: "inline-block" }} />
        Live
      </div>

      <div className="theme-toggle" role="group" aria-label="Color theme">
        <button
          type="button"
          className={theme === "light" ? "active" : ""}
          onClick={() => setThemeMode("light")}
          aria-label="Light mode"
        >
          <Sun style={{ width: 16, height: 16 }} />
        </button>
        <button
          type="button"
          className={theme === "dark" ? "active" : ""}
          onClick={() => setThemeMode("dark")}
          aria-label="Dark mode"
        >
          <Moon style={{ width: 16, height: 16 }} />
        </button>
      </div>

      {hitlCount > 0 && (
        <Link href="/investigation?tab=hitl" className="status-live" style={{ color: "var(--r-sec2)", borderColor: "rgba(197,48,48,0.35)", background: "rgba(197,48,48,0.12)" }}>
          {hitlCount} HITL
        </Link>
      )}

      <button type="button" className="icon-btn" aria-label="Notifications">
        <Bell style={{ width: 16, height: 16 }} />
        {hitlCount > 0 && (
          <span style={{ position: "absolute", top: 5, right: 5, width: 5, height: 5, background: "var(--r-sec2)", borderRadius: "50%" }} />
        )}
      </button>

      <Link href="/agents" className="icon-btn" aria-label="AI">
        <Bot style={{ width: 16, height: 16 }} />
      </Link>

      <Link href="/settings" className="icon-btn" aria-label="Settings">
        <Settings style={{ width: 16, height: 16 }} />
      </Link>

      <button
        type="button"
        onClick={logout}
        title="Sign out"
        style={{
          width: 28,
          height: 28,
          borderRadius: 4,
          background: "var(--purple-deep)",
          border: "1px solid var(--border-glow)",
          color: "var(--text-on-brand)",
          fontSize: 11,
          fontWeight: 700,
          fontFamily: "IBM Plex Mono, monospace",
          cursor: "pointer",
        }}
      >
        {initials}
      </button>
    </header>
  );
}
