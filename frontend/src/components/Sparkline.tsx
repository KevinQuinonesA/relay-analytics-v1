import { useState } from "react";

import type { WeekPoint } from "../api";
import { eventTypeCounts } from "../eventTypes";
import { formatWeek, plural } from "../format";

interface Props {
  label: string; // what the series is, e.g. the location name
  weeks: WeekPoint[]; // baseline weeks then this week, oldest first; null = no history yet
  typicalLow: number | null;
  typicalHigh: number | null;
  size?: "row" | "header";
}

// same width in rows and header so the header sparkline sits in the rows' sparkline column
const SIZES = { row: { width: 120, height: 32 }, header: { width: 120, height: 40 } };
const PAD = 5; // room for the 8px this-week dot

function describe(label: string, weeks: WeekPoint[], low: number | null, high: number | null): string {
  const last = weeks.length - 1;
  const points = weeks
    .map((w, i) => (w.count === null ? null : `${formatWeek(w.start, w.end)}: ${w.count}${i === last ? " (this week)" : ""}`))
    .filter((p) => p !== null);
  const range = low === null || high === null ? "" : ` Typical range ${low}–${high}.`;
  return `${label}, weekly events: ${points.join(", ")}.${range}`;
}

// No axes: the shaded band is the typical range, the accent dot is this week. Scaling to
// pixels is rendering only; every number comes from the API.
export function Sparkline({ label, weeks, typicalLow, typicalHigh, size = "row" }: Props) {
  const [hovered, setHovered] = useState<number | null>(null);
  const { width, height } = SIZES[size];
  const last = weeks.length - 1;
  // Scaled to its own data and band (no zero baseline: it's a line, not bars), so the shape
  // is legible whether a series runs 0-10 or 70-90.
  const values = weeks.map((w) => w.count).filter((c): c is number => c !== null);
  if (typicalLow !== null && typicalHigh !== null) values.push(typicalLow, typicalHigh);
  const min = Math.min(...values, Infinity);
  const max = Math.max(...values, -Infinity);
  const span = max > min ? max - min : 1;
  const step = (width - 2 * PAD) / Math.max(1, last);
  const x = (i: number) => PAD + i * step;
  const y = (v: number) => (max > min ? height - PAD - ((v - min) * (height - 2 * PAD)) / span : height / 2);

  // one path segment per run of weeks with data
  const path = weeks
    .map((w, i) => (w.count === null ? null : `${i > 0 && weeks[i - 1]?.count !== null ? "L" : "M"}${x(i)},${y(w.count)}`))
    .filter((d) => d !== null)
    .join(" ");

  const hoveredWeek = hovered === null ? null : weeks[hovered];
  return (
    <span className="sparkline">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img"
           aria-label={describe(label, weeks, typicalLow, typicalHigh)}>
        {typicalLow !== null && typicalHigh !== null && (
          <rect data-testid="spark-band" className="spark-band" x={PAD} width={width - 2 * PAD}
                y={y(typicalHigh) - 1} height={Math.max(2, y(typicalLow) - y(typicalHigh) + 2)} rx={2} />
        )}
        <path className="spark-line" d={path} />
        {hovered !== null && hovered !== last && hoveredWeek?.count != null && (
          <circle className="spark-hover" cx={x(hovered)} cy={y(hoveredWeek.count)} r={3} />
        )}
        {weeks[last]?.count != null && (
          <circle className="spark-current" cx={x(last)} cy={y(weeks[last].count)} r={4} />
        )}
        {weeks.map((w, i) =>
          w.count === null ? null : (
            <rect key={w.start} data-testid="spark-hit" className="spark-hit" x={x(i) - step / 2} y={0}
                  width={step} height={height}
                  onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)} />
          ),
        )}
      </svg>
      {hoveredWeek && hoveredWeek.count !== null && (
        <span role="tooltip" className="spark-tooltip" style={{ left: x(hovered ?? 0) }}>
          <span className="spark-tooltip-total">
            {`${formatWeek(hoveredWeek.start, hoveredWeek.end)}: ${plural(hoveredWeek.count, "event")}`}
          </span>
          {hoveredWeek.by_event_type && (
            <span className="spark-tooltip-types">{eventTypeCounts(hoveredWeek.by_event_type, "title")}</span>
          )}
        </span>
      )}
    </span>
  );
}
