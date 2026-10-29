import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";

import { type Account, ApiError, getJson, type WeeklySummary, weeklySummaryUrl } from "./api";

// --- URL state: the query string is the single source of truth -----------------------

export interface Selection {
  account: number | null;
  asOf: string | null;
}

const URL_CHANGE = "relay:urlchange";

function subscribe(onChange: () => void): () => void {
  window.addEventListener("popstate", onChange);
  window.addEventListener(URL_CHANGE, onChange);
  return () => {
    window.removeEventListener("popstate", onChange);
    window.removeEventListener(URL_CHANGE, onChange);
  };
}

function parseSelection(search: string): Selection {
  const params = new URLSearchParams(search);
  const account = Number(params.get("account"));
  return {
    account: Number.isInteger(account) && account > 0 ? account : null,
    asOf: params.get("as_of") || null,
  };
}

export function useSelection(): [Selection, (next: Partial<Selection>) => void] {
  const search = useSyncExternalStore(subscribe, () => window.location.search);
  const selection = useMemo(() => parseSelection(search), [search]);
  const update = useCallback((next: Partial<Selection>) => {
    const params = new URLSearchParams(window.location.search);
    for (const [key, value] of [
      ["account", next.account],
      ["as_of", next.asOf],
    ] as const) {
      if (value === undefined) continue;
      if (value === null) params.delete(key);
      else params.set(key, String(value));
    }
    const query = params.toString();
    window.history.pushState(null, "", query ? `?${query}` : window.location.pathname);
    window.dispatchEvent(new Event(URL_CHANGE));
  }, []);
  return [selection, update];
}

// --- data fetching --------------------------------------------------------------------

export type FetchState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; httpStatus: number | null }
  | { status: "success"; data: T };

function useFetch<T>(url: string | null): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ status: "idle" });
  useEffect(() => {
    if (url === null) {
      setState({ status: "idle" });
      return;
    }
    const controller = new AbortController();
    setState({ status: "loading" });
    getJson<T>(url, controller.signal)
      .then((data) => setState({ status: "success", data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({ status: "error", httpStatus: error instanceof ApiError ? error.status : null });
      });
    return () => controller.abort();
  }, [url]);
  return state;
}

export function useAccounts(): FetchState<Account[]> {
  return useFetch<Account[]>("/api/accounts");
}

export function useWeeklySummary(account: number | null, asOf: string | null): FetchState<WeeklySummary> {
  return useFetch<WeeklySummary>(account === null ? null : weeklySummaryUrl(account, asOf));
}
