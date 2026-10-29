import type { EventType, WeeklySummary } from "../api";
import { Sparkline } from "./Sparkline";

export const EVENT_TYPE_LABEL: Record<EventType, { title: string; short: string }> = {
  call_received: { title: "Calls", short: "calls" },
  lead_created: { title: "Leads", short: "leads" },
  appointment_set: { title: "Appointments", short: "appointments" },
};

const ORDER: EventType[] = ["call_received", "lead_created", "appointment_set"];

// Context only: the account's totals are never flagged.
export function AccountTotals({ summary }: { summary: WeeklySummary }) {
  const all = summary.account_total;
  const allRange = all.typical_low === null || all.typical_high === null ? "" : ` (typical ${all.typical_low}–${all.typical_high})`;
  return (
    <>
      <p className="account-total">
        <span>{`All events ${all.count}${allRange}`}</span>
        <Sparkline label="All events" weeks={all.weeks} typicalLow={all.typical_low} typicalHigh={all.typical_high} size="header" />
      </p>
      <ul className="totals" aria-label="Account totals">
      {ORDER.map((type) => {
        const t = summary.account_totals[type];
        const range = t.typical_low === null || t.typical_high === null ? "" : ` (typical ${t.typical_low}–${t.typical_high})`;
        return <li key={type}>{`${EVENT_TYPE_LABEL[type].title} ${t.count}${range}`}</li>;
      })}
      </ul>
    </>
  );
}

export function eventTypeCounts(counts: Record<EventType, number>): string {
  return ORDER.map((type) => `${EVENT_TYPE_LABEL[type].short} ${counts[type]}`).join(" · ");
}
