import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "SupportLens", template: "%s | SupportLens" },
  description: "AI-powered customer support analysis platform",
};

const NAV_LINKS = [
  { href: "/",       label: "Dashboard" },
  { href: "/chat",   label: "Chat"      },
  { href: "/traces", label: "Traces"    },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 text-slate-900 antialiased`}>

        {/* ── Top navigation ── */}
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur-sm">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">

            {/* Logo */}
            <Link href="/" className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
                <svg className="h-4 w-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </div>
              <span className="text-lg font-bold text-slate-900">SupportLens</span>
              <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700">
                beta
              </span>
            </Link>

            {/* Nav links */}
            <nav className="flex items-center gap-1">
              {NAV_LINKS.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
                >
                  {label}
                </Link>
              ))}
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="ml-2 rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-500 transition hover:border-slate-300 hover:text-slate-700"
              >
                API Docs ↗
              </a>
            </nav>
          </div>
        </header>

        {/* ── Page content ── */}
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>

      </body>
    </html>
  );
}
