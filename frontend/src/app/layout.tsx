import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LexVerify — Verification-First Legal AI",
  description: "High-precision legal intelligence. Every answer backed by verified citations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
