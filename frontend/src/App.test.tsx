import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Account, LocationWeek, WeekPoint, WeeklySummary } from "./api";
import { App } from "./App";

const ACCOUNTS: Account[] = [
  { id: 6, name: "Metro Collision Centers", timezone: "America/New_York", location_count: 15 },
  { id: 15, name: "Sierra Pest Solutions", timezone: "America/Phoenix", location_count: 3 },
];

// The 8 baseline weeks plus this week, as the API sends them.
const WEEK_BOUNDS: [string, string][] = [
  ["2026-05-25", "2026-05-31"], ["2026-06-01", "2026-06-07"], ["2026-06-08", "2026-06-14"],
  ["2026-06-15", "2026-06-21"], ["2026-06-22", "2026-06-28"], ["2026-06-29", "2026-07-05"],
  ["2026-07-06", "2026-07-12"], ["2026-07-13", "2026-07-19"], ["2026-07-20", "2026-07-26"],
];

type Types = [number, number, number]; // calls, leads, appointments

// Per-type counts default to all calls, so they always add up to the count.
function weeks(counts: (number | null)[], types: (Types | null)[] = []): WeekPoint[] {
  return WEEK_BOUNDS.map(([start, end], i) => {
    const count = counts[i] ?? null;
    const [c, l, a] = types[i] ?? [count ?? 0, 0, 0];
    return { start, end, count,
             by_event_type: count === null ? null : { call_received: c, lead_created: l, appointment_set: a } };
  });
}

function location(overrides: Partial<LocationWeek> & Pick<LocationWeek, "location" | "status">): LocationWeek {
  return {
    weeks: weeks([5, 6, 7, 6, 5, 8, 6, 7, 6]),
    flagged: false,
    count: 6,
    median: 6,
    typical_low: 5,
    typical_high: 9,
    distance: 0,
    by_event_type: { call_received: 4, lead_created: 1, appointment_set: 1 },
    ...overrides,
  };
}

// Deliberately not alphabetical: the UI must keep the API's order.
const SUMMARY: WeeklySummary = {
  account: { id: 15, name: "Sierra Pest Solutions", timezone: "America/Phoenix" },
  as_of: "2026-07-27",
  week: { start: "2026-07-20", end: "2026-07-26" },
  baseline: { start: "2026-05-25", end: "2026-07-19", weeks: 8 },
  thresholds: { baseline_weeks: 8, range_trim: 1, min_baseline_median: 5, min_flag_distance: 0.3 },
  account_totals: {
    call_received: { count: 9, median: 12, typical_low: 11, typical_high: 19 },
    lead_created: { count: 6, median: 3.5, typical_low: 2, typical_high: 7 },
    appointment_set: { count: 5, median: null, typical_low: null, typical_high: null },
  },
  account_total: {
    count: 20, median: 19, typical_low: 15, typical_high: 24,
    weeks: weeks([15, 33, 23, 14, 24, 16, 19, 19, 20],
                 [[11, 0, 4], [21, 7, 5], [19, 3, 1], [11, 2, 1], [12, 8, 4], [12, 2, 2], [12, 4, 3], [9, 6, 4], [9, 6, 5]]),
  },
  locations: [
    location({ location: "Site C", status: "above_typical", flagged: true, count: 12, typical_low: 4, typical_high: 7,
               by_event_type: { call_received: 7, lead_created: 3, appointment_set: 2 },
               weeks: weeks([4, 5, 10, 4, 6, 6, 7, 6, 12],
                            [[3, 0, 1], [1, 2, 2], [8, 1, 1], [1, 2, 1], [2, 2, 2], [5, 0, 1], [4, 2, 1], [2, 2, 2], [7, 3, 2]]) }),
    location({ location: "Site B", status: "below_typical", flagged: true, count: 2, typical_low: 4, typical_high: 12 }),
    location({ location: "Site D", status: "slightly_below", count: 5, typical_low: 6, typical_high: 9 }),
    location({ location: "Site A", status: "typical" }),
    location({ location: "Site F", status: "too_little_activity", median: 4, distance: null }),
    location({ location: "Site E", status: "insufficient_history", median: null, typical_low: null,
               typical_high: null, distance: null, weeks: weeks([null, null, null, null, null, null, null, null, 6]) }),
  ],
};

type Route = { status: number; body: unknown } | (() => Promise<never>);

function mockApi(routes: Record<string, Route>) {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    const route = routes[url];
    if (route === undefined) return Promise.resolve(new Response("not mocked", { status: 500 }));
    if (typeof route === "function") return route();
    return Promise.resolve(new Response(JSON.stringify(route.body), { status: route.status }));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const summaryUrl = (account: number, asOf?: string) =>
  `/api/accounts/${account}/weekly-summary${asOf ? `?as_of=${asOf}` : ""}`;

function requestedUrls(fetchMock: ReturnType<typeof mockApi>) {
  return fetchMock.mock.calls.map(([input]) => String(input));
}

function openAt(search: string) {
  window.history.replaceState(null, "", `/${search}`);
  return render(<App />);
}

async function statCards() {
  const list = await screen.findByRole("list", { name: /account totals/i });
  return within(list).getAllByRole("listitem");
}

async function locationRows() {
  const list = await screen.findByRole("list", { name: /locations/i });
  return within(list).getAllByRole("listitem");
}

beforeEach(() => {
  mockApi({ "/api/accounts": { status: 200, body: ACCOUNTS }, [summaryUrl(15)]: { status: 200, body: SUMMARY } });
});

describe("weekly summary", () => {
  it("lists locations in the order the API returns", async () => {
    openAt("?account=15");
    const rows = await locationRows();
    expect(rows.map((row) => within(row).getByText(/^Site /).textContent)).toEqual([
      "Site C", "Site B", "Site D", "Site A", "Site F", "Site E",
    ]);
  });

  it("marks flagged locations with an icon and text, and shows the range for slightly-outside ones", async () => {
    openAt("?account=15");
    const [above, below, slightly] = await locationRows();
    expect(above?.textContent).toContain("▲");
    expect(within(above!).getByText("Above typical")).toBeTruthy();
    expect(within(above!).getByText("12 events")).toBeTruthy();
    expect(within(above!).getByText("typical 4–7")).toBeTruthy();
    expect(below?.textContent).toContain("▼");
    expect(within(below!).getByText("Below typical")).toBeTruthy();
    expect(within(slightly!).getByText("Slightly below")).toBeTruthy();
    expect(within(slightly!).getByText("typical 6–9")).toBeTruthy();
    expect(slightly?.textContent).not.toMatch(/[▲▼]/);
  });

  it("labels the columns above the location rows", async () => {
    openAt("?account=15");
    await locationRows();
    const headers = screen.getByTestId("location-columns");
    expect(Array.from(headers.children, (c) => c.textContent)).toEqual(["Status", "Location", "Last 9 weeks", "This week"]);
  });

  it("gives slightly-outside rows a lighter outline arrow and typical rows none", async () => {
    mockApi({
      "/api/accounts": { status: 200, body: ACCOUNTS },
      [summaryUrl(15)]: { status: 200, body: { ...SUMMARY, locations: [
        location({ location: "Site C", status: "above_typical", flagged: true }),
        location({ location: "Site B", status: "slightly_above" }),
        location({ location: "Site D", status: "slightly_below" }),
        location({ location: "Site A", status: "typical" }),
        location({ location: "Site F", status: "too_little_activity", distance: null }),
      ] } },
    });
    openAt("?account=15");
    const icons = (await locationRows()).map((row) => row.textContent?.match(/[▲▼△▽]/g)?.join("") ?? "");
    expect(icons).toEqual(["▲", "△", "▽", "", ""]);
  });

  it("explains locations that can't be assessed", async () => {
    openAt("?account=15");
    const rows = await locationRows();
    expect(within(rows[4]!).getByText("Too little activity to tell")).toBeTruthy();
    expect(within(rows[4]!).getByText("typically under 5 a week")).toBeTruthy();
    expect(within(rows[5]!).getByText("Not enough history yet")).toBeTruthy();
    expect(within(rows[5]!).getByText("needs 8 full weeks of history")).toBeTruthy();
  });

  it("shows each location's per-type counts", async () => {
    openAt("?account=15");
    const [siteC] = await locationRows();
    expect(within(siteC!).getByText("calls 7 · leads 3 · appointments 2")).toBeTruthy();
  });

  it("shows the account totals as stat cards: label, big number, typical range", async () => {
    openAt("?account=15");
    const cards = await statCards();
    expect(cards).toHaveLength(4);
    const expectCard = (card: HTMLElement, label: string, value: string, range: string) => {
      expect(within(card).getByText(label)).toBeTruthy();
      expect(within(card).getByText(value)).toBeTruthy();
      expect(within(card).getByText(range)).toBeTruthy();
    };
    expectCard(cards[0]!, "All events", "20", "typical 15–24");
    expectCard(cards[1]!, "Calls", "9", "typical 11–19");
    expectCard(cards[2]!, "Leads", "6", "typical 2–7");
    expectCard(cards[3]!, "Appointments", "5", "no typical range yet");
  });

  it("shows the week and the baseline it is compared with", async () => {
    openAt("?account=15");
    expect(
      await screen.findByText("Week of Jul 20 – 26 · compared with the previous 8 weeks (May 25 – Jul 19)"),
    ).toBeTruthy();
  });
});

describe("attention line", () => {
  function withLocations(locations: LocationWeek[]) {
    mockApi({
      "/api/accounts": { status: 200, body: ACCOUNTS },
      [summaryUrl(15)]: { status: 200, body: { ...SUMMARY, locations } },
    });
    openAt("?account=15");
  }

  it("says so at the top when no location is flagged", async () => {
    withLocations([
      location({ location: "Site A", status: "typical" }),
      location({ location: "Site B", status: "slightly_above", distance: 0.1 }),
      location({ location: "Site C", status: "too_little_activity", distance: null }),
    ]);
    expect((await screen.findByRole("status")).textContent).toBe("No locations need attention this week.");
  });

  it("doesn't claim all is well when no location could be assessed", async () => {
    withLocations([
      location({ location: "Site A", status: "too_little_activity", distance: null }),
      location({ location: "Site B", status: "insufficient_history", median: null, distance: null }),
    ]);
    expect((await screen.findByRole("status")).textContent).toBe(
      "Not enough activity to assess any location this week.",
    );
  });

  it("shows no such line when something is flagged", async () => {
    openAt("?account=15");
    await locationRows();
    expect(screen.queryByRole("status")).toBeNull();
  });
});

describe("as-of control", () => {
  it("explains which week the date selects", async () => {
    openAt("?account=15");
    const input = (await screen.findByLabelText("As of")) as HTMLInputElement;
    const hint = screen.getByText("Shows the last complete week (Mon–Sun) before this date.");
    expect(input.getAttribute("aria-describedby")).toBe(hint.id);
  });
});

describe("sparklines", () => {
  it("describes each location's 9 weeks, marking this week", async () => {
    openAt("?account=15");
    const [siteC] = await locationRows();
    const chart = within(siteC!).getByRole("img");
    expect(chart.getAttribute("aria-label")).toBe(
      "Site C, weekly events: May 25–31: 4, Jun 1–7: 5, Jun 8–14: 10, Jun 15–21: 4, Jun 22–28: 6, " +
        "Jun 29–Jul 5: 6, Jul 6–12: 7, Jul 13–19: 6, Jul 20–26: 12 (this week). Typical range 4–7.",
    );
  });

  it("shows the week and its count when hovering a point", async () => {
    openAt("?account=15");
    const [siteC] = await locationRows();
    const points = within(siteC!).getAllByTestId("spark-hit");
    expect(points).toHaveLength(9);
    fireEvent.mouseEnter(points[5]!);
    const tooltip = within(siteC!).getByRole("tooltip");
    expect(within(tooltip).getByText("Jun 29–Jul 5: 6 events")).toBeTruthy();
    expect(within(tooltip).getByText("Calls 5 · Leads 0 · Appointments 1")).toBeTruthy();
    fireEvent.mouseEnter(points[8]!);
    expect(within(within(siteC!).getByRole("tooltip")).getByText("Jul 20–26: 12 events")).toBeTruthy();
    expect(within(within(siteC!).getByRole("tooltip")).getByText("Calls 7 · Leads 3 · Appointments 2")).toBeTruthy();
    fireEvent.mouseLeave(points[8]!);
    expect(within(siteC!).queryByRole("tooltip")).toBeNull();
  });

  it("skips weeks before a location's history and draws no range without a baseline", async () => {
    openAt("?account=15");
    const siteE = (await locationRows())[5]!;
    expect(within(siteE).getAllByTestId("spark-hit")).toHaveLength(1);
    expect(within(siteE).queryByTestId("spark-band")).toBeNull();
    expect(within(siteE).getByRole("img").getAttribute("aria-label")).toBe(
      "Site E, weekly events: Jul 20–26: 6 (this week).",
    );
    const siteC = (await locationRows())[0]!;
    expect(within(siteC).getByTestId("spark-band")).toBeTruthy();
  });

  it("breaks the account total's week down by type on hover", async () => {
    openAt("?account=15");
    const total = (await statCards())[0]!;
    const points = within(total).getAllByTestId("spark-hit");
    fireEvent.mouseEnter(points[8]!);
    const tooltip = within(total).getByRole("tooltip");
    expect(within(tooltip).getByText("Jul 20–26: 20 events")).toBeTruthy();
    expect(within(tooltip).getByText("Calls 9 · Leads 6 · Appointments 5")).toBeTruthy();
  });

  it("shows the account total with its own sparkline in the All events card", async () => {
    openAt("?account=15");
    const chart = within((await statCards())[0]!).getByRole("img");
    expect(chart.getAttribute("aria-label")).toMatch(/^All events, weekly events: May 25–31: 15, .* Jul 20–26: 20 \(this week\)\. Typical range 15–24\.$/);
  });
});

describe("URL state", () => {
  it("reads account and as-of from the URL", async () => {
    const fetchMock = mockApi({
      "/api/accounts": { status: 200, body: ACCOUNTS },
      [summaryUrl(6, "2026-04-20")]: { status: 200, body: { ...SUMMARY, as_of: "2026-04-20" } },
    });
    openAt("?account=6&as_of=2026-04-20");
    await locationRows();
    expect(requestedUrls(fetchMock)).toContain(summaryUrl(6, "2026-04-20"));
    expect((screen.getByLabelText("As of") as HTMLInputElement).value).toBe("2026-04-20");
    await waitFor(() => expect((screen.getByLabelText("Account") as HTMLSelectElement).value).toBe("6"));
  });

  it("writes a new account to the URL and keeps the as-of", async () => {
    const fetchMock = mockApi({
      "/api/accounts": { status: 200, body: ACCOUNTS },
      [summaryUrl(6, "2026-04-20")]: { status: 200, body: SUMMARY },
      [summaryUrl(15, "2026-04-20")]: { status: 200, body: SUMMARY },
    });
    openAt("?account=6&as_of=2026-04-20");
    const select = (await screen.findByLabelText("Account")) as HTMLSelectElement;
    await waitFor(() => expect(select.disabled).toBe(false));
    fireEvent.change(select, { target: { value: "15" } });
    expect(window.location.search).toBe("?account=15&as_of=2026-04-20");
    await waitFor(() => expect(requestedUrls(fetchMock)).toContain(summaryUrl(15, "2026-04-20")));
  });

  it("'Latest data' removes the as-of and shows the date the API resolved", async () => {
    mockApi({
      "/api/accounts": { status: 200, body: ACCOUNTS },
      [summaryUrl(15, "2026-04-20")]: { status: 200, body: { ...SUMMARY, as_of: "2026-04-20" } },
      [summaryUrl(15)]: { status: 200, body: SUMMARY },
    });
    openAt("?account=15&as_of=2026-04-20");
    await locationRows();
    fireEvent.click(screen.getByRole("button", { name: "Latest data" }));
    expect(window.location.search).toBe("?account=15");
    await waitFor(() => expect((screen.getByLabelText("As of") as HTMLInputElement).value).toBe("2026-07-27"));
  });

  it("follows browser back/forward", async () => {
    const fetchMock = mockApi({
      "/api/accounts": { status: 200, body: ACCOUNTS },
      [summaryUrl(6)]: { status: 200, body: SUMMARY },
      [summaryUrl(15)]: { status: 200, body: SUMMARY },
    });
    openAt("?account=15");
    await locationRows();
    act(() => {
      window.history.pushState(null, "", "/?account=6");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await waitFor(() => expect(requestedUrls(fetchMock)).toContain(summaryUrl(6)));
  });

  it("asks for an account when none is in the URL and fetches no summary", async () => {
    const fetchMock = mockApi({ "/api/accounts": { status: 200, body: ACCOUNTS } });
    openAt("");
    expect(await screen.findByText(/choose an account/i, { selector: "p" })).toBeTruthy();
    expect(requestedUrls(fetchMock)).toEqual(["/api/accounts"]);
  });
});

describe("loading, error and empty states", () => {
  it("shows loading while the summary is on its way", async () => {
    mockApi({ "/api/accounts": { status: 200, body: ACCOUNTS }, [summaryUrl(15)]: () => new Promise<never>(() => {}) });
    openAt("?account=15");
    expect(await screen.findByText("Loading…", { selector: "p" })).toBeTruthy();
  });

  it.each([
    [404, "Account not found."],
    [422, "That as-of date isn't valid. Use YYYY-MM-DD."],
    [500, "Couldn't load the weekly summary. Try again."],
  ])("shows a message for HTTP %i", async (status, message) => {
    mockApi({ "/api/accounts": { status: 200, body: ACCOUNTS }, [summaryUrl(15)]: { status, body: {} } });
    openAt("?account=15");
    expect((await screen.findByRole("alert")).textContent).toBe(message);
  });

  it("says so when the account has no activity", async () => {
    mockApi({
      "/api/accounts": { status: 200, body: ACCOUNTS },
      [summaryUrl(15)]: { status: 200, body: { ...SUMMARY, locations: [] } },
    });
    openAt("?account=15");
    expect(await screen.findByText("No activity recorded for this account yet.")).toBeTruthy();
  });
});
