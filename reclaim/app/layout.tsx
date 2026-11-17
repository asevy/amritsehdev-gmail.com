import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "@fontsource-variable/fraunces/opsz.css";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "RECLAIM — strength, body composition and metabolic health", template: "%s · RECLAIM" },
  description:
    "A measured programme for strength, body composition and metabolic health: assessment, a personal Blueprint, coaching, local partner sessions, and clinician-led care from an independent medical practice where appropriate.",
  robots: { index: false, follow: false }, // prototype: keep out of search until counsel sign-off
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-CA" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="min-h-screen font-sans">
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-paper">
          Skip to content
        </a>
        {children}
      </body>
    </html>
  );
}
