export default function TicketsPage() {
  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-slate-900">Support Tickets</h2>
        <button className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          New Ticket
        </button>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-slate-400">
        <p className="text-sm">No tickets yet — logic coming soon.</p>
      </div>
    </div>
  );
}
