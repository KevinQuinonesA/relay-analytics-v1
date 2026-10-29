import type { LocationWeek, Status, WeeklySummary } from "../api";
import { plural } from "../format";
import { eventTypeCounts } from "./AccountTotals";

const STATUS_LABEL: Record<Status, string> = {
  above_typical: "Above typical",
  below_typical: "Below typical",
  slightly_above: "Slightly above",
  slightly_below: "Slightly below",
  typical: "Typical",
  too_little_activity: "Too little activity to tell",
  insufficient_history: "Not enough history yet",
};

const STATUS_ICON: Partial<Record<Status, string>> = {
  above_typical: "▲",
  below_typical: "▼",
};

function Detail({ location, summary }: { location: LocationWeek; summary: WeeklySummary }) {
  switch (location.status) {
    case "too_little_activity":
      return <>typically under {summary.thresholds.min_baseline_median} a week</>;
    case "insufficient_history":
      return <>needs {plural(summary.baseline.weeks, "full week")} of history</>;
    default:
      return (
        <>
          typical {location.typical_low}–{location.typical_high}
        </>
      );
  }
}

const ASSESSED: Status[] = ["above_typical", "below_typical", "slightly_above", "slightly_below", "typical"];

// Shown only when nothing is flagged, so the admin doesn't have to scan the list to find out.
export function AttentionLine({ summary }: { summary: WeeklySummary }) {
  const { locations } = summary;
  if (locations.length === 0 || locations.some((l) => l.flagged)) return null;
  const anyAssessed = locations.some((l) => ASSESSED.includes(l.status));
  return (
    <p role="status" className="attention">
      {anyAssessed
        ? "No locations need attention this week."
        : "Not enough activity to assess any location this week."}
    </p>
  );
}

export function LocationList({ summary }: { summary: WeeklySummary }) {
  if (summary.locations.length === 0) {
    return <p className="empty">No activity recorded for this account yet.</p>;
  }
  return (
    <ul className="locations" aria-label="Locations, most unusual first">
      {summary.locations.map((location) => (
        <li key={location.location} className={`location status-${location.status}${location.flagged ? " flagged" : ""}`}>
          <span className="status">
            {STATUS_ICON[location.status] && (
              <span className="icon" aria-hidden="true">
                {STATUS_ICON[location.status]}
              </span>
            )}
            {STATUS_LABEL[location.status]}
          </span>
          <span className="name">{location.location}</span>
          <span className="count">{plural(location.count, "event")}</span>
          <span className="detail">
            <Detail location={location} summary={summary} />
          </span>
          <span className="types">{eventTypeCounts(location.by_event_type)}</span>
        </li>
      ))}
    </ul>
  );
}
