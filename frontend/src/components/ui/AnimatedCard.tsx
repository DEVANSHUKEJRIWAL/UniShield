"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface AnimatedCardProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  glass?: boolean;
  gradientBorder?: boolean;
  float?: boolean;
  onClick?: () => void;
}

export function AnimatedCard({
  children,
  className,
  delay = 0,
  glass,
  gradientBorder,
  float,
  onClick,
}: AnimatedCardProps) {
  return (
    <motion.div
      onClick={onClick}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.4, 0, 0.2, 1] }}
      whileHover={{ y: -2, boxShadow: "var(--shadow-soft)" }}
      className={cn(
        "ac-card relative",
        glass && "backdrop-blur-xl",
        gradientBorder && "before:absolute before:inset-0 before:rounded-[var(--radius-lg)] before:p-[1px] before:bg-gradient-to-br before:from-[var(--purple-mid)] before:to-[var(--magenta)] before:-z-10",
        float && "animate-float",
        className
      )}
    >
      {children}
    </motion.div>
  );
}
