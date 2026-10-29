import type { EventType } from "./api";

export const EVENT_TYPE_LABEL: Record<EventType, { title: string; short: string }> = {
  call_received: { title: "Calls", short: "calls" },
  lead_created: { title: "Leads", short: "leads" },
  appointment_set: { title: "Appointments", short: "appointments" },
};

export const EVENT_TYPE_ORDER: EventType[] = ["call_received", "lead_created", "appointment_set"];

// "calls 7 · leads 3 · appointments 2" (rows) or "Calls 7 · Leads 3 · Appointments 2" (tooltips)
export function eventTypeCounts(counts: Record<EventType, number>, style: "short" | "title" = "short"): string {
  return EVENT_TYPE_ORDER.map((type) => `${EVENT_TYPE_LABEL[type][style]} ${counts[type]}`).join(" · ");
}
