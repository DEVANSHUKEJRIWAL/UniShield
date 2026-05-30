"use client";

import { AnimatePresence, motion } from "framer-motion";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { ParticleBackground } from "./ParticleBackground";
import { Navbar } from "./Navbar";
import { Toaster } from "sonner";

const pageVariants = {
  initial: { opacity: 0, x: 20, filter: "blur(4px)" },
  animate: { opacity: 1, x: 0, filter: "blur(0px)" },
  exit: { opacity: 0, x: -20, filter: "blur(4px)" },
};

const pageTransition = {
  type: "tween" as const,
  ease: [0.4, 0, 0.2, 1] as [number, number, number, number],
  duration: 0.25,
};

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <>
      <ParticleBackground />
      <Navbar hitlCount={2} />
      <AnimatePresence mode="wait">
        <motion.div key={pathname} className="relative z-10 min-h-screen pt-16">
          <motion.div
            initial={{ scaleX: 0, originX: 0 }}
            animate={{ scaleX: 1 }}
            exit={{ scaleX: 0, originX: 1 }}
            transition={{ duration: 0.25 }}
            className="fixed left-0 right-0 top-16 z-50 h-0.5 bg-gradient-to-r from-[var(--violet)] to-[var(--magenta)]"
          />
          <motion.main
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
            className="px-6 pb-12 pt-6"
          >
            {children}
          </motion.main>
        </motion.div>
      </AnimatePresence>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            color: "var(--text-primary)",
          },
        }}
      />
    </>
  );
}
