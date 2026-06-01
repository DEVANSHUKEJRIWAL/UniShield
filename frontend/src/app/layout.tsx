import type { Metadata } from "next";
import "./globals.css";
import "../styles/admin-center.css";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "UniShield — AI Defense Platform",
  description: "AI-native cybersecurity defense platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
