// Types mirror the backend's Pydantic response models (backend/relay/api.py).

export type Status =
  | "above_typical"
  | "below_typical"
  | "slightly_above"
  | "slightly_below"
  | "typical"
  | "too_little_activity"
  | "insufficient_history";

export interface Account {
  id: number;
  name: string;
  timezone: string;
  location_count: number;
}

export interface Period {
  start: string; // YYYY-MM-DD
  end: string;
}

export interface LocationWeek {
  location: string;
  status: Status;
  flagged: boolean;
  count: number;
  median: number | null;
  typical_low: number | null;
  typical_high: number | null;
  distance: number | null;
}

export interface WeeklySummary {
  account: { id: number; name: string; timezone: string };
  as_of: string;
  week: Period;
  baseline: Period & { weeks: number };
  thresholds: {
    baseline_weeks: number;
    range_trim: number;
    min_baseline_median: number;
    min_flag_distance: number;
  };
  locations: LocationWeek[]; // already ranked by the API
}

export class ApiError extends Error {
  constructor(readonly status: number) {
    super(`Request failed with status ${status}`);
  }
}

export async function getJson<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new ApiError(response.status);
  return (await response.json()) as T;
}

export function weeklySummaryUrl(account: number, asOf: string | null): string {
  const query = asOf ? `?${new URLSearchParams({ as_of: asOf })}` : "";
  return `/api/accounts/${account}/weekly-summary${query}`;
}
