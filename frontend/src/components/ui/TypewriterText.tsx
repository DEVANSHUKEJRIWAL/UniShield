"use client";

import { useEffect, useState } from "react";

export function TypewriterText({ text, speed = 40 }: { text: string; speed?: number }) {
  const [display, setDisplay] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    setDisplay("");
    setDone(false);
    let i = 0;
    const id = setInterval(() => {
      if (i < text.length) {
        setDisplay(text.slice(0, i + 1));
        i++;
      } else {
        setDone(true);
        clearInterval(id);
      }
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);

  return (
    <span className="font-mono text-sm text-[var(--text-secondary)]">
      {display}
      {!done && <span className="animate-pulse text-[var(--violet)]">|</span>}
    </span>
  );
}
