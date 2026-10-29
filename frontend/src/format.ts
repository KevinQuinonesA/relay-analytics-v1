// Display formatting only; no numbers are computed here.

const dayMonth = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
const day = new Intl.DateTimeFormat("en-US", { day: "numeric", timeZone: "UTC" });

// API dates are calendar dates (YYYY-MM-DD); parse as UTC so the browser's zone can't shift them.
function parseDate(value: string): Date {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(Date.UTC(y ?? 0, (m ?? 1) - 1, d ?? 1));
}

export function formatRange(start: string, end: string): string {
  const s = parseDate(start);
  const e = parseDate(end);
  const sameMonth = s.getUTCMonth() === e.getUTCMonth();
  return `${dayMonth.format(s)} – ${sameMonth ? day.format(e) : dayMonth.format(e)}`;
}

export function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}
