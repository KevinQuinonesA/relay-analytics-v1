import { AccountTotals } from "./components/AccountTotals";
import { Controls } from "./components/Controls";
import { AttentionLine, LocationList } from "./components/LocationList";
import { formatRange, plural } from "./format";
import { type FetchState, useAccounts, useSelection, useWeeklySummary } from "./hooks";
import type { WeeklySummary } from "./api";

function SummaryView({ state }: { state: FetchState<WeeklySummary> }) {
  switch (state.status) {
    case "idle":
      return <p className="empty">Choose an account to see how last week compares with its usual activity.</p>;
    case "loading":
      return <p className="empty">Loading…</p>;
    case "error":
      return (
        <p className="error" role="alert">
          {state.httpStatus === 404
            ? "Account not found."
            : state.httpStatus === 422
              ? "That as-of date isn't valid. Use YYYY-MM-DD."
              : "Couldn't load the weekly summary. Try again."}
        </p>
      );
    case "success": {
      const s = state.data;
      return (
        <section aria-labelledby="summary-title">
          <div className="summary-head">
            <h2 id="summary-title">{s.account.name}</h2>
            <p className="period">
              Week of {formatRange(s.week.start, s.week.end)} · compared with the previous{" "}
              {plural(s.baseline.weeks, "week")} ({formatRange(s.baseline.start, s.baseline.end)})
            </p>
          </div>
          <AttentionLine summary={s} />
          <AccountTotals summary={s} />
          <LocationList summary={s} />
        </section>
      );
    }
  }
}

export function App() {
  const [selection, setSelection] = useSelection();
  const accounts = useAccounts();
  const summary = useWeeklySummary(selection.account, selection.asOf);

  return (
    <main>
      <h1>Weekly activity</h1>
      <Controls
        accounts={accounts}
        selection={selection}
        resolvedAsOf={summary.status === "success" ? summary.data.as_of : null}
        onChange={setSelection}
      />
      <SummaryView state={summary} />
    </main>
  );
}
