"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import CategoryBadge from "@/components/CategoryBadge";
import Spinner from "@/components/Spinner";
import { analyticsApi, tracesApi } from "@/lib/api";
import type { AnalyticsResponse, Trace } from "@/types";

const BAR_COLORS: Record<string, string> = {
  Billing:          "bg-blue-500",
  Refund:           "bg-emerald-500",
  "Account Access": "bg-amber-500",
  Cancellation:     "bg-rose-500",
  "General Inquiry":"bg-purple-500",
};

function formatTime(ms: number) {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)  return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [traces,    setTraces]    = useState<Trace[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState<string | null>(null);

  useEffect(() => {
    Promise.all([analyticsApi.get(), tracesApi.list()])
      .then(([a, t]) => {
        setAnalytics(a);
        setTraces(t.slice(0, 8));
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3 text-center">
        <div className="rounded-full bg-rose-100 p-3">
          <svg className="h-6 w-6 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-slate-700">Could not reach the API</p>
        <p className="max-w-xs text-xs text-slate-400">{error}</p>
        <button onClick={() => window.location.reload()} className="mt-1 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">

      {/* ── Page header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="mt-0.5 text-sm text-slate-500">Overview of your support conversation analytics</p>
        </div>
        <Link
          href="/chat"
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 transition"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Chat
        </Link>
      </div>

      {/* ── Stat cards ── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="Total Traces"
          value={analytics?.total_traces ?? 0}
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
            </svg>
          }
          color="brand"
        />
        <StatCard
          label="Avg Response Time"
          value={analytics ? formatTime(Math.round(analytics.average_response_time)) : "—"}
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          color="amber"
        />
        <StatCard
          label="Categories"
          value={analytics?.breakdown.length ?? 0}
          icon={
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.568 3H5.25A2.25 2.25 0 003 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 005.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 009.568 3z" />
            </svg>
          }
          color="purple"
        />
      </div>

      {/* ── Category breakdown ── */}
      {analytics && analytics.breakdown.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Category Breakdown
          </h2>
          <div className="space-y-3">
            {analytics.breakdown.map((row) => (
              <div key={row.category}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="font-medium text-slate-700">{row.category}</span>
                  <span className="text-slate-400">
                    {row.count} &nbsp;·&nbsp; {row.percentage}%
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${BAR_COLORS[row.category] ?? "bg-slate-400"}`}
                    style={{ width: `${row.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Recent traces ── */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Recent Traces</h2>
          <Link href="/traces" className="text-xs font-medium text-brand-600 hover:text-brand-700">
            View all →
          </Link>
        </div>

        {traces.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-slate-400">
            No traces yet.{" "}
            <Link href="/chat" className="text-brand-600 hover:underline">Start a chat</Link> to create one.
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {traces.map((t) => (
              <li key={t.id} className="flex items-start gap-4 px-6 py-4 hover:bg-slate-50 transition">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-800">{t.user_message}</p>
                  <p className="mt-0.5 truncate text-xs text-slate-400">{t.bot_response}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1.5">
                  <CategoryBadge category={t.category} size="sm" />
                  <span className="text-xs text-slate-400">
                    {formatTime(t.response_time_ms)} · {timeAgo(t.timestamp)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

    </div>
  );
}

/* ── Sub-components ── */

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: "brand" | "amber" | "purple";
}

const CARD_COLORS = {
  brand:  { bg: "bg-brand-50",  icon: "text-brand-600",  ring: "ring-brand-100"  },
  amber:  { bg: "bg-amber-50",  icon: "text-amber-600",  ring: "ring-amber-100"  },
  purple: { bg: "bg-purple-50", icon: "text-purple-600", ring: "ring-purple-100" },
};

function StatCard({ label, value, icon, color }: StatCardProps) {
  const c = CARD_COLORS[color];
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg ring-1 ${c.bg} ${c.icon} ${c.ring}`}>
          {icon}
        </div>
        <div>
          <p className="text-xs font-medium text-slate-500">{label}</p>
          <p className="mt-0.5 text-2xl font-bold text-slate-900">{value}</p>
        </div>
      </div>
    </div>
  );
}
