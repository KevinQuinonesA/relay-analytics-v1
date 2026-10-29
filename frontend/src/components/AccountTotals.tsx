import type { WeeklySummary } from "../api";
import { EVENT_TYPE_LABEL, EVENT_TYPE_ORDER as ORDER } from "../eventTypes";
import { Sparkline } from "./Sparkline";

function typicalRange(low: number | null, high: number | null): string {
  return low === null || high === null ? "no typical range yet" : `typical ${low}–${high}`;
}

// Stat cards for the account. Context only: the account's totals are never flagged.
export function AccountTotals({ summary }: { summary: WeeklySummary }) {
  const all = summary.account_total;
  return (
    <ul className="stat-cards" aria-label="Account totals">
      <li className="stat-card stat-card-all">
        <span className="stat-label">All events</span>
        <span className="stat-main">
          <span className="stat-value">{all.count}</span>
          <Sparkline label="All events" weeks={all.weeks} typicalLow={all.typical_low} typicalHigh={all.typical_high}
                     size="header" />
        </span>
        <span className="stat-range">{typicalRange(all.typical_low, all.typical_high)}</span>
      </li>
      {ORDER.map((type) => {
        const t = summary.account_totals[type];
        return (
          <li key={type} className="stat-card">
            <span className="stat-label">{EVENT_TYPE_LABEL[type].title}</span>
            <span className="stat-value">{t.count}</span>
            <span className="stat-range">{typicalRange(t.typical_low, t.typical_high)}</span>
          </li>
        );
      })}
    </ul>
  );
}
