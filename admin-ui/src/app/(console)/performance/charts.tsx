import type { components } from "@/lib/api/schema";
import { formatCount, formatMs } from "@/lib/format";

import styles from "../dashboard.module.css";

// Plain SVG charts, drawn on the server (no chart library, no browser JavaScript). Each chart has a text
// summary for screen readers; hovering a bar or point shows its values (native SVG <title>).

type Point = components["schemas"]["TimeseriesPoint"];
type Tick = (iso: string) => string;

const W = 600;
const H = 200;

/** The plot with value labels on the left (top, middle, 0) and time labels underneath. */
function Plot({
  points,
  tick,
  top,
  middle,
  children,
}: {
  points: Point[];
  tick: Tick;
  top: string;
  middle: string;
  children: React.ReactNode;
}) {
  const mid = points[Math.floor(points.length / 2)];
  return (
    <div className={styles.plot}>
      <div className={styles.yAxis} aria-hidden="true">
        <span>{top}</span>
        <span>{middle}</span>
        <span>0</span>
      </div>
      {children}
      <div className={styles.axis} aria-hidden="true">
        <span>{tick(points[0].bucket_start)}</span>
        <span>{tick(mid.bucket_start)}</span>
        <span>{tick(points[points.length - 1].bucket_start)}</span>
      </div>
    </div>
  );
}

/** Half of a count, without a needless ".0" (3 → "1.5", 4 → "2"). */
function half(n: number): string {
  return Number.isInteger(n / 2) ? formatCount(n / 2) : (n / 2).toFixed(1);
}

export function RequestsChart({ points, tick, bucket }: { points: Point[]; tick: Tick; bucket: string }) {
  const most = Math.max(1, ...points.map((p) => p.requests));
  const total = points.reduce((sum, p) => sum + p.requests, 0);
  const errors = points.reduce((sum, p) => sum + p.errors, 0);
  const slot = W / points.length;
  const bar = Math.max(1, slot * 0.7);

  return (
    <figure className={styles.chart}>
      <p className={styles.kpiNote}>Requests per {bucket}</p>
      <Plot points={points} tick={tick} top={formatCount(most)} middle={half(most)}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`${formatCount(total)} requests and ${formatCount(errors)} errors in this window.`}
      >
        <line x1="0" x2={W} y1={H / 2} y2={H / 2} className={styles.gridLine} />
        {points.map((p, i) => {
          const x = i * slot + (slot - bar) / 2;
          const h = (p.requests / most) * H;
          const e = (p.errors / most) * H;
          return (
            <g key={p.bucket_start}>
              <title>{`${tick(p.bucket_start)}: ${formatCount(p.requests)} requests, ${formatCount(p.errors)} errors`}</title>
              <rect x={x} y={H - h} width={bar} height={h} rx="2" className={styles.barRequests} />
              {e > 0 && <rect x={x} y={H - e} width={bar} height={e} rx="2" className={styles.barErrors} />}
            </g>
          );
        })}
      </svg>
      </Plot>
      <figcaption className={styles.legend}>
        <span>
          <i className={styles.swatchRequests} aria-hidden="true" /> Requests
        </span>
        <span>
          <i className={styles.swatchErrors} aria-hidden="true" /> Errors
        </span>
      </figcaption>
    </figure>
  );
}

const SERIES = [
  { key: "p50_ms", label: "Typical (p50)", line: styles.lineP50 },
  { key: "p95_ms", label: "Slow (p95)", line: styles.lineP95 },
  { key: "queue_p95_ms", label: "Queue wait (p95)", line: styles.lineQueue },
] as const;

export function TimesChart({ points, tick }: { points: Point[]; tick: Tick }) {
  const values = points.flatMap((p) => SERIES.map((s) => p[s.key])).filter((v): v is number => v !== null);
  const most = Math.max(1, ...values);
  const slot = W / points.length;
  const x = (i: number) => i * slot + slot / 2;
  const y = (ms: number) => H - (ms / most) * (H - 6) - 3;

  // One path per series; an empty bucket (null) breaks the line instead of dropping it to zero.
  const path = (key: (typeof SERIES)[number]["key"]) =>
    points
      .map((p, i) => {
        const v = p[key];
        if (v === null) return "";
        const previous = i > 0 ? points[i - 1][key] : null;
        return `${previous === null ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
      })
      .join(" ");

  return (
    <figure className={styles.chart}>
      <p className={styles.kpiNote}>Time per request</p>
      <Plot points={points} tick={tick} top={formatMs(most)} middle={formatMs(most / 2)}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Response times; the slowest bucket reached ${formatMs(most)}.`}
      >
        <line x1="0" x2={W} y1={H / 2} y2={H / 2} className={styles.gridLine} />
        {SERIES.map((s) => (
          <g key={s.key} className={s.line}>
            <path d={path(s.key)} />
            {points.map((p, i) =>
              p[s.key] === null ? null : (
                <circle key={p.bucket_start} cx={x(i)} cy={y(p[s.key] as number)} r="3">
                  <title>{`${tick(p.bucket_start)} ${s.label}: ${formatMs(p[s.key])}`}</title>
                </circle>
              ),
            )}
          </g>
        ))}
      </svg>
      </Plot>
      <figcaption className={styles.legend}>
        {SERIES.map((s) => (
          <span key={s.key}>
            <svg width="22" height="8" aria-hidden="true" className={s.line}>
              <path d="M1 4 H21" />
            </svg>
            {s.label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
