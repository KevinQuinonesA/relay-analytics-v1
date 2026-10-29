import type { Account } from "../api";
import type { FetchState, Selection } from "../hooks";

interface Props {
  accounts: FetchState<Account[]>;
  selection: Selection;
  // as_of the API resolved to; shown when the URL has none
  resolvedAsOf: string | null;
  onChange: (next: Partial<Selection>) => void;
}

export function Controls({ accounts, selection, resolvedAsOf, onChange }: Props) {
  return (
    <div className="controls">
      <label>
        Account
        {accounts.status === "success" ? (
          <select
            value={selection.account ?? ""}
            onChange={(e) => onChange({ account: e.target.value ? Number(e.target.value) : null })}
          >
            <option value="">Choose an account…</option>
            {accounts.data.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        ) : (
          <select disabled>
            <option>{accounts.status === "error" ? "Couldn't load accounts" : "Loading…"}</option>
          </select>
        )}
      </label>
      <label>
        As of
        <input
          type="date"
          aria-describedby="as-of-hint"
          value={selection.asOf ?? resolvedAsOf ?? ""}
          onChange={(e) => onChange({ asOf: e.target.value || null })}
        />
      </label>
      <button type="button" disabled={selection.asOf === null} onClick={() => onChange({ asOf: null })}>
        Latest data
      </button>
      <p id="as-of-hint" className="hint">
        Shows the last complete week (Mon–Sun) before this date.
      </p>
    </div>
  );
}
