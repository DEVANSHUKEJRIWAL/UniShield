"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Shield } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ParticleBackground } from "@/components/ParticleBackground";
import { GradientText } from "@/components/ui/primitives";

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
      setError("Invalid credentials — run ./scripts/fix-login.sh on the API");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden">
      <ParticleBackground />
      <div className="absolute right-6 top-6 z-50">
        <ThemeToggle />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 40, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
        className="relative z-10 w-full max-w-md rounded-3xl border border-[var(--border-default)] p-10 backdrop-blur-xl"
        style={{
          background: "color-mix(in srgb, var(--bg-surface) 90%, transparent)",
          boxShadow: "0 0 60px var(--violet-glow)",
        }}
      >
        <motion.div
          animate={{ rotate: [0, 5, -5, 0] }}
          transition={{ repeat: Infinity, duration: 6, ease: "easeInOut" }}
          className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl"
          style={{
            background: "linear-gradient(135deg, var(--violet), var(--magenta))",
            boxShadow: "0 0 30px var(--violet-glow)",
          }}
        >
          <Shield size={28} className="text-white" />
        </motion.div>

        <h1 className="text-center text-3xl font-extrabold">
          <GradientText>UniShield</GradientText>
        </h1>
        <p className="mt-2 text-center font-mono text-xs text-[var(--text-muted)]">AI-NATIVE CYBER DEFENSE</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <motion.input
            whileFocus={{ boxShadow: "0 0 0 2px var(--violet-glow)" }}
            name="email"
            type="email"
            defaultValue="analyst@meridian.com"
            required
            placeholder="Email"
            className="w-full rounded-xl border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-3 text-sm outline-none transition"
          />
          <motion.input
            whileFocus={{ boxShadow: "0 0 0 2px var(--violet-glow)" }}
            name="password"
            type="password"
            defaultValue="analyst123"
            required
            placeholder="Password"
            className="w-full rounded-xl border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-3 text-sm outline-none transition"
          />
          {error && <p className="text-center text-sm text-[var(--red)]">{error}</p>}
          <motion.button
            whileHover={{ scale: 1.02, boxShadow: "0 0 30px var(--violet-glow)" }}
            whileTap={{ scale: 0.97 }}
            type="submit"
            disabled={loading}
            className="w-full rounded-xl py-3 text-sm font-bold text-white disabled:opacity-50"
            style={{ background: "linear-gradient(135deg, var(--violet), var(--magenta))" }}
          >
            {loading ? "Authenticating..." : "Enter Mission Control"}
          </motion.button>
        </form>

        <p className="mt-6 text-center font-mono text-[10px] text-[var(--text-muted)]">
          analyst@meridian.com / analyst123
        </p>
      </motion.div>
    </div>
  );
}
