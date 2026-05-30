"use client";

import CountUp from "react-countup";

export function AnimatedNumber({
  value,
  suffix = "",
  prefix = "",
  decimals = 0,
}: {
  value: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
}) {
  return (
    <span style={{ fontFamily: "var(--font-display)" }}>
      {prefix}
      <CountUp end={value} duration={1.8} decimals={decimals} separator="," />
      {suffix}
    </span>
  );
}
