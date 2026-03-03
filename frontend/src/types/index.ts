export type Category =
  | "Billing"
  | "Refund"
  | "Account Access"
  | "Cancellation"
  | "General Inquiry";

export interface Trace {
  id: string;
  user_message: string;
  bot_response: string;
  category: Category;
  timestamp: string;
  response_time_ms: number;
}

export interface CategoryBreakdown {
  category: string;
  count: number;
  percentage: number;
}

export interface AnalyticsResponse {
  total_traces: number;
  average_response_time: number;
  breakdown: CategoryBreakdown[];
}
