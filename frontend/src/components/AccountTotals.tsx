import type { EventType, WeeklySummary } from "../api";

export const EVENT_TYPE_LABEL: Record<EventType, { title: string; short: string }> = {
  call_received: { title: "Calls", short: "calls" },
  lead_created: { title: "Leads", short: "leads" },
  appointment_set: { title: "Appointments", short: "appointments" },
};

const ORDER: EventType[] = ["call_received", "lead_created", "appointment_set"];

// Context only: the account's totals are never flagged.
export function AccountTotals({ summary }: { summary: WeeklySummary }) {
  return (
    <ul className="totals" aria-label="Account totals">
      {ORDER.map((type) => {
        const t = summary.account_totals[type];
        const range = t.typical_low === null || t.typical_high === null ? "" : ` (typical ${t.typical_low}–${t.typical_high})`;
        return <li key={type}>{`${EVENT_TYPE_LABEL[type].title} ${t.count}${range}`}</li>;
      })}
    </ul>
  );
}

export function eventTypeCounts(counts: Record<EventType, number>): string {
  return ORDER.map((type) => `${EVENT_TYPE_LABEL[type].short} ${counts[type]}`).join(" · ");
}
