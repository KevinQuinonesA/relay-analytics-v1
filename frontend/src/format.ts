// Display formatting only; no numbers are computed here.

const dayMonth = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
const day = new Intl.DateTimeFormat("en-US", { day: "numeric", timeZone: "UTC" });

// API dates are calendar dates (YYYY-MM-DD); parse as UTC so the browser's zone can't shift them.
function parseDate(value: string): Date {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(Date.UTC(y ?? 0, (m ?? 1) - 1, d ?? 1));
}

function range(start: string, end: string, separator: string): string {
  const s = parseDate(start);
  const e = parseDate(end);
  const sameMonth = s.getUTCMonth() === e.getUTCMonth();
  return `${dayMonth.format(s)}${separator}${sameMonth ? day.format(e) : dayMonth.format(e)}`;
}

// "Jul 20 – 26", for headings
export function formatRange(start: string, end: string): string {
  return range(start, end, " – ");
}

// "Jul 20–26" or "Jun 29–Jul 5", for compact week labels
export function formatWeek(start: string, end: string): string {
  return range(start, end, "–");
}

export function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}
