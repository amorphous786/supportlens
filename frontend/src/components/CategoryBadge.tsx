import type { Category } from "@/types";

const STYLES: Record<Category, string> = {
  Billing:          "bg-blue-50 text-blue-700 ring-blue-200",
  Refund:           "bg-emerald-50 text-emerald-700 ring-emerald-200",
  "Account Access": "bg-amber-50 text-amber-700 ring-amber-200",
  Cancellation:     "bg-rose-50 text-rose-700 ring-rose-200",
  "General Inquiry":"bg-purple-50 text-purple-700 ring-purple-200",
};

const DOT: Record<Category, string> = {
  Billing:          "bg-blue-500",
  Refund:           "bg-emerald-500",
  "Account Access": "bg-amber-500",
  Cancellation:     "bg-rose-500",
  "General Inquiry":"bg-purple-500",
};

interface Props {
  category: string;
  size?: "sm" | "md";
}

export default function CategoryBadge({ category, size = "md" }: Props) {
  const cat = category as Category;
  const style = STYLES[cat] ?? "bg-slate-100 text-slate-600 ring-slate-200";
  const dot   = DOT[cat]   ?? "bg-slate-400";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 ring-1 font-medium whitespace-nowrap
        ${size === "sm" ? "py-0.5 text-xs" : "py-1 text-xs"}
        ${style}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {category}
    </span>
  );
}
