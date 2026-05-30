import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "UniShield — AI Defense Platform",
  description: "AI-native cybersecurity defense platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
