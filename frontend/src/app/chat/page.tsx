"use client";

import type { Metadata } from "next";
import { useEffect, useRef, useState } from "react";

import CategoryBadge from "@/components/CategoryBadge";
import Spinner from "@/components/Spinner";
import { tracesApi } from "@/lib/api";
import type { Trace } from "@/types";

interface Message {
  role: "user" | "bot";
  text: string;
  trace?: Trace;
}

function formatTime(ms: number) {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

export default function ChatPage() {
  const [messages,  setMessages]  = useState<Message[]>([]);
  const [input,     setInput]     = useState("");
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState<string | null>(null);
  const bottomRef   = useRef<HTMLDivElement>(null);
  const inputRef    = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);

    try {
      const trace = await tracesApi.create(text);
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: trace.bot_response, trace },
      ]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setError(msg);
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Sorry, I couldn't process your request right now. Please try again." },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex h-[calc(100vh-73px)] flex-col">

      {/* ── Header ── */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Chat</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Each message is processed by Llama 3 and automatically classified
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={() => { setMessages([]); setError(null); }}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-500 hover:bg-slate-100 transition"
          >
            Clear session
          </button>
        )}
      </div>

      {/* ── Message area ── */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-sm">

        {/* Empty state */}
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-100">
              <svg className="h-7 w-7 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-slate-800">Start a support conversation</p>
              <p className="mt-1 text-sm text-slate-400">
                Ask about billing, refunds, account access, or anything else
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 text-left">
              {SAMPLE_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => { setInput(p); inputRef.current?.focus(); }}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 transition text-left"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.length > 0 && (
          <div className="space-y-1 p-4">
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}

            {/* Loading bubble */}
            {loading && (
              <div className="flex items-start gap-3 py-2">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100">
                  <svg className="h-4 w-4 text-brand-600" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                  </svg>
                </div>
                <div className="rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <Spinner size="sm" />
                    <span className="text-xs text-slate-400">Generating response…</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* ── Error banner ── */}
      {error && (
        <div className="mt-2 flex items-center gap-2 rounded-lg bg-rose-50 px-4 py-2.5 text-sm text-rose-700 ring-1 ring-rose-200">
          <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          {error}
        </div>
      )}

      {/* ── Input bar ── */}
      <div className="mt-3 flex items-end gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm ring-0 focus-within:ring-2 focus-within:ring-brand-400 transition">
        <textarea
          ref={inputRef}
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a support question… (Enter to send, Shift+Enter for new line)"
          className="flex-1 resize-none bg-transparent text-sm text-slate-800 placeholder-slate-400 outline-none"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || loading}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <svg className="h-4 w-4 rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
          </svg>
        </button>
      </div>
      <p className="mt-1.5 text-center text-xs text-slate-400">
        Responses are generated locally via Llama 3 · Each conversation is saved as a trace
      </p>

    </div>
  );
}

/* ── Message bubble ── */
function MessageBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end py-1">
        <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-sm text-white shadow-sm">
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 py-1">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100">
        <svg className="h-4 w-4 text-brand-600" fill="currentColor" viewBox="0 0 24 24">
          <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
        </svg>
      </div>
      <div className="max-w-[75%] space-y-2">
        <div className="rounded-2xl rounded-tl-sm bg-slate-100 px-4 py-2.5 text-sm text-slate-800 shadow-sm">
          {message.text}
        </div>
        {message.trace && (
          <div className="flex items-center gap-2">
            <CategoryBadge category={message.trace.category} size="sm" />
            <span className="text-xs text-slate-400">
              {formatTime(message.trace.response_time_ms)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

const SAMPLE_PROMPTS = [
  "Why was I charged twice this month?",
  "I'd like to request a refund for my last payment",
  "I can't log in — my password isn't working",
  "How do I cancel my subscription?",
];
