import type { Metadata } from "next";
import { IBM_Plex_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const ibmPlexSans = IBM_Plex_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
  preload: true,
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
  preload: false, // Only load when actually used for code elements
});

export const metadata: Metadata = {
  title: "UN Wallet — Multi-Bank Data Migration Platform",
  description:
    "Production-grade interbank ETL platform for secure, auditable multi-format data migration across banking systems.",
  keywords: ["bank migration", "ETL", "data migration", "UN Wallet", "interbank"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${ibmPlexSans.variable} ${jetbrainsMono.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{
          __html: `
            try {
              const theme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
              document.documentElement.classList.toggle('dark', theme === 'dark');
            } catch(e) {}
          `,
        }} />
      </head>
      <body suppressHydrationWarning className="min-h-screen bg-background text-foreground antialiased font-[family-name:var(--font-sans)]">
        {children}
      </body>
    </html>
  );
}
