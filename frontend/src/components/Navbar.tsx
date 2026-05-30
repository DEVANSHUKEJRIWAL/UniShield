"use client";

import { motion, useSpring, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { ThemeToggle } from "./ThemeToggle";
import { Bell, Shield } from "lucide-react";
import { useAuth } from "@/lib/auth";

const NAV_LINKS = [
  { href: "/dashboard", label: "SOC" },
  { href: "/agents", label: "Agents" },
  { href: "/alerts", label: "Alerts" },
  { href: "/investigation", label: "Investigation" },
  { href: "/reporting", label: "Reporting" },
  { href: "/compliance", label: "Compliance" },
  { href: "/network", label: "Network" },
  { href: "/deployment", label: "Deploy" },
  { href: "/cloud", label: "Cloud" },
];

export function Navbar({ hitlCount = 2 }: { hitlCount?: number }) {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const logoRef = useRef<HTMLDivElement>(null);
  const { email, logout } = useAuth();
  const logoX = useSpring(0, { stiffness: 200, damping: 20 });
  const logoY = useSpring(0, { stiffness: 200, damping: 20 });

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const initials = email?.slice(0, 2).toUpperCase() ?? "US";

  return (
    <motion.nav
      animate={{ height: scrolled ? 52 : 64 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="fixed left-0 right-0 top-0 z-50 flex items-center gap-6 border-b border-[var(--border-subtle)] px-6 backdrop-blur-xl"
      style={{ background: "color-mix(in srgb, var(--bg-secondary) 88%, transparent)" }}
    >
      <motion.div
        ref={logoRef}
        style={{ x: logoX, y: logoY }}
        onMouseMove={(e) => {
          const rect = logoRef.current?.getBoundingClientRect();
          if (!rect) return;
          const dx = e.clientX - (rect.left + rect.width / 2);
          const dy = e.clientY - (rect.top + rect.height / 2);
          if (Math.sqrt(dx * dx + dy * dy) < 80) {
            logoX.set(dx * 0.25);
            logoY.set(dy * 0.25);
          }
        }}
        onMouseLeave={() => {
          logoX.set(0);
          logoY.set(0);
        }}
        className="mr-4 flex cursor-pointer select-none items-center gap-2.5"
      >
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <motion.div
            whileHover={{ rotate: 15, scale: 1.1 }}
            transition={{ type: "spring", stiffness: 400, damping: 15 }}
            className="flex h-8 w-8 items-center justify-center rounded-xl"
            style={{
              background: "linear-gradient(135deg, var(--violet), var(--magenta))",
              boxShadow: "0 0 20px var(--violet-glow)",
            }}
          >
            <Shield size={15} className="text-white" />
          </motion.div>
          <div>
            <div className="text-[15px] font-bold leading-none" style={{ fontFamily: "var(--font-display)" }}>
              UniShield
            </div>
            <div className="mt-0.5 text-[9px] font-semibold uppercase tracking-widest text-[var(--violet-light)] font-mono">
              AI Defense
            </div>
          </div>
        </Link>
      </motion.div>

      <div className="relative flex items-center gap-1">
        {NAV_LINKS.map((link) => {
          const isActive = pathname.startsWith(link.href);
          return (
            <Link key={link.href} href={link.href}>
              <motion.div
                className="relative cursor-pointer rounded-lg px-3 py-1.5 text-[13px] font-medium"
                style={{ color: isActive ? "var(--text-primary)" : "var(--text-secondary)" }}
                whileHover={{ color: "var(--text-primary)" }}
              >
                {isActive && (
                  <motion.div
                    layoutId="nav-active"
                    className="absolute inset-0 rounded-lg"
                    style={{ background: "var(--violet-dim)", border: "1px solid rgba(124,58,237,0.2)" }}
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative z-10">{link.label}</span>
              </motion.div>
            </Link>
          );
        })}
      </div>

      <div className="flex-1" />

      <AnimatePresence>
        {hitlCount > 0 && (
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            className="flex cursor-pointer items-center gap-2 rounded-full px-3 py-1.5 text-[12px] font-bold"
            style={{ background: "var(--red-dim)", border: "1px solid rgba(244,63,94,0.3)", color: "var(--red)" }}
          >
            <motion.div
              animate={{ scale: [1, 1.4, 1] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
              className="h-2 w-2 rounded-full"
              style={{ background: "var(--red)", boxShadow: "0 0 8px var(--red)" }}
            />
            {hitlCount} HITL
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        className="flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)]"
      >
        <Bell size={15} />
      </motion.button>

      <ThemeToggle />

      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={logout}
        title="Sign out"
        className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl text-[12px] font-bold text-white"
        style={{
          background: "linear-gradient(135deg, var(--violet), var(--magenta))",
          boxShadow: "0 0 16px var(--violet-glow)",
        }}
      >
        {initials}
      </motion.button>
    </motion.nav>
  );
}
