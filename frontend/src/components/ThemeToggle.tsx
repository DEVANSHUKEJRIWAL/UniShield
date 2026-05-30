"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState, useCallback, useRef, useEffect } from "react";
import { Sun, Moon } from "lucide-react";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [isAnimating, setIsAnimating] = useState(false);
  const [ripple, setRipple] = useState<{ x: number; y: number } | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const saved = localStorage.getItem("unishield-theme") as "dark" | "light" | null;
    const initial = saved ?? "dark";
    setTheme(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  const toggle = useCallback(() => {
    if (isAnimating) return;
    const rect = buttonRef.current?.getBoundingClientRect();
    if (!rect) return;

    setIsAnimating(true);
    setRipple({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 });

    setTimeout(() => {
      const next = theme === "dark" ? "light" : "dark";
      setTheme(next);
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("unishield-theme", next);
    }, 300);

    setTimeout(() => {
      setIsAnimating(false);
      setRipple(null);
    }, 700);
  }, [theme, isAnimating]);

  return (
    <>
      <AnimatePresence>
        {ripple && (
          <motion.div
            initial={{ scale: 0, opacity: 1 }}
            animate={{ scale: 80, opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
            style={{
              position: "fixed",
              left: ripple.x - 20,
              top: ripple.y - 20,
              width: 40,
              height: 40,
              borderRadius: "50%",
              background: theme === "dark" ? "#f8f9ff" : "#080b12",
              zIndex: 9998,
              pointerEvents: "none",
            }}
          />
        )}
      </AnimatePresence>

      <motion.button
        ref={buttonRef}
        onClick={toggle}
        whileTap={{ scale: 0.85 }}
        whileHover={{ scale: 1.1 }}
        style={{ zIndex: 9999, position: "relative" }}
        className="relative flex h-12 w-12 cursor-pointer items-center justify-center overflow-hidden rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface)]"
        aria-label="Toggle theme"
      >
        <motion.div
          className="absolute inset-0 opacity-0"
          style={{ background: "linear-gradient(135deg, var(--violet), var(--magenta))" }}
          whileHover={{ opacity: 0.15 }}
        />
        <AnimatePresence mode="wait">
          {theme === "dark" ? (
            <motion.div
              key="sun"
              initial={{ rotate: -90, opacity: 0, scale: 0.5 }}
              animate={{ rotate: 0, opacity: 1, scale: 1 }}
              exit={{ rotate: 90, opacity: 0, scale: 0.5 }}
              transition={{ duration: 0.3, ease: "backOut" }}
            >
              <Sun size={18} className="text-[var(--amber)]" />
            </motion.div>
          ) : (
            <motion.div
              key="moon"
              initial={{ rotate: 90, opacity: 0, scale: 0.5 }}
              animate={{ rotate: 0, opacity: 1, scale: 1 }}
              exit={{ rotate: -90, opacity: 0, scale: 0.5 }}
              transition={{ duration: 0.3, ease: "backOut" }}
            >
              <Moon size={18} className="text-[var(--violet-light)]" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
    </>
  );
}
