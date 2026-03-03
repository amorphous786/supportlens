import type { AnalyticsResponse, Category, Trace } from "@/types";

const BASE_URL =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  // 204 No Content has no body
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const tracesApi = {
  list: (category?: Category | ""): Promise<Trace[]> => {
    const params = category ? `?category=${encodeURIComponent(category)}` : "";
    return apiFetch<Trace[]>(`/api/v1/traces/${params}`);
  },
  get: (id: string): Promise<Trace> => apiFetch<Trace>(`/api/v1/traces/${id}`),
  delete: (id: string): Promise<void> =>
    apiFetch<void>(`/api/v1/traces/${id}`, { method: "DELETE" }),
};

export const analyticsApi = {
  get: (): Promise<AnalyticsResponse> =>
    apiFetch<AnalyticsResponse>("/api/v1/analytics/"),
};

// ── SSE streaming types ───────────────────────────────────────────────────────

type TokenEvent = { type: "token"; content: string };
type DoneEvent  = { type: "done";  trace: Trace };
type ErrorEvent = { type: "error"; detail: string };
export type StreamEvent = TokenEvent | DoneEvent | ErrorEvent;

/**
 * POST /api/v1/traces/stream, parse SSE, and fire onEvent for each message.
 * Throws if the HTTP request itself fails (non-2xx before streaming starts).
 */
export async function streamTrace(
  userMessage: string,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/v1/traces/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_message: userMessage }),
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Stream error ${res.status}: ${body || res.statusText}`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body from stream endpoint");

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep the last (possibly incomplete) line in the buffer
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const event = JSON.parse(line.slice(6)) as StreamEvent;
          onEvent(event);
        } catch {
          // Ignore malformed SSE lines
        }
      }
    }
  } finally {
    reader.cancel().catch(() => undefined);
  }
}
