"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import CategoryBadge from "@/components/CategoryBadge";
import Spinner from "@/components/Spinner";
import { tracesApi } from "@/lib/api";
import type { Category, Trace } from "@/types";

const CATEGORIES: Array<{ label: string; value: Category | "" }> = [
  { label: "All",             value: ""                },
  { label: "Billing",         value: "Billing"         },
  { label: "Refund",          value: "Refund"          },
  { label: "Account Access",  value: "Account Access"  },
  { label: "Cancellation",    value: "Cancellation"    },
  { label: "General Inquiry", value: "General Inquiry" },
];

function formatTime(ms: number) {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) +
    " " + d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

export default function TracesPage() {
  const [traces,   setTraces]   = useState<Trace[]>([]);
  const [filter,   setFilter]   = useState<Category | "">("");
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    tracesApi.list(filter)
      .then(setTraces)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filter]);

  function toggleRow(id: string) {
    setExpanded((prev) => (prev === id ? null : id));
  }

  return (
    <div className="space-y-6">

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Traces</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Full history of support conversations
          </p>
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

      {/* ── Category filter pills ── */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map(({ label, value }) => (
          <button
            key={label}
            onClick={() => setFilter(value)}
            className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition ring-1 ${
              filter === value
                ? "bg-brand-600 text-white ring-brand-600"
                : "bg-white text-slate-600 ring-slate-200 hover:ring-slate-300"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── Content ── */}
      {loading ? (
        <div className="flex h-48 items-center justify-center">
          <Spinner size="lg" />
        </div>
      ) : error ? (
        <div className="flex h-48 flex-col items-center justify-center gap-2 text-center">
          <p className="text-sm font-medium text-rose-600">Failed to load traces</p>
          <p className="text-xs text-slate-400">{error}</p>
          <button
            onClick={() => setFilter(filter)}
            className="mt-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Retry
          </button>
        </div>
      ) : traces.length === 0 ? (
        <div className="flex h-48 flex-col items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white text-center">
          <p className="text-sm font-medium text-slate-600">No traces found</p>
          <p className="text-xs text-slate-400">
            {filter
              ? `No conversations classified as "${filter}" yet`
              : "Start a chat to create your first trace"}
          </p>
          {!filter && (
            <Link href="/chat" className="mt-1 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
              Start chatting
            </Link>
          )}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">

          {/* Table header */}
          <div className="grid grid-cols-[1fr_140px_100px_80px] gap-4 border-b border-slate-100 bg-slate-50 px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
            <span>Message</span>
            <span>Category</span>
            <span>Date</span>
            <span className="text-right">Time</span>
          </div>

          {/* Rows */}
          <ul className="divide-y divide-slate-100">
            {traces.map((trace) => (
              <TraceRow
                key={trace.id}
                trace={trace}
                isExpanded={expanded === trace.id}
                onToggle={() => toggleRow(trace.id)}
              />
            ))}
          </ul>

          <div className="border-t border-slate-100 bg-slate-50 px-5 py-2.5 text-xs text-slate-400">
            {traces.length} trace{traces.length !== 1 ? "s" : ""}
            {filter ? ` in "${filter}"` : " total"}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Trace row with expandable detail ── */
interface TraceRowProps {
  trace: Trace;
  isExpanded: boolean;
  onToggle: () => void;
}

function TraceRow({ trace, isExpanded, onToggle }: TraceRowProps) {
  return (
    <li>
      {/* Summary row */}
      <button
        onClick={onToggle}
        className="grid w-full grid-cols-[1fr_140px_100px_80px] gap-4 px-5 py-3.5 text-left transition hover:bg-slate-50"
      >
        <span className="truncate text-sm font-medium text-slate-800">
          {trace.user_message}
        </span>
        <span>
          <CategoryBadge category={trace.category} size="sm" />
        </span>
        <span className="text-xs text-slate-400">{formatDate(trace.timestamp)}</span>
        <span className="text-right text-xs font-medium text-slate-500">
          {formatTime(trace.response_time_ms)}
        </span>
      </button>

      {/* Expanded conversation */}
      {isExpanded && (
        <div className="border-t border-slate-100 bg-slate-50 px-5 py-4 space-y-3">
          <div className="flex justify-end">
            <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-sm text-white shadow-sm">
              {trace.user_message}
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100">
              <svg className="h-3.5 w-3.5 text-brand-600" fill="currentColor" viewBox="0 0 24 24">
                <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <div className="space-y-2">
              <div className="max-w-[80%] rounded-2xl rounded-tl-sm bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm ring-1 ring-slate-200">
                {trace.bot_response}
              </div>
              <div className="flex items-center gap-2">
                <CategoryBadge category={trace.category} size="sm" />
                <span className="text-xs text-slate-400">
                  Response in {formatTime(trace.response_time_ms)}
                </span>
              </div>
            </div>
          </div>
          <p className="text-right text-xs text-slate-400">
            ID: {trace.id} · {formatDate(trace.timestamp)}
          </p>
        </div>
      )}
    </li>
  );
}
