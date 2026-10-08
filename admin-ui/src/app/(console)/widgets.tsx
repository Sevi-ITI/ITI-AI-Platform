import type { components } from "@/lib/api/schema";
import { formatMb, formatUptime } from "@/lib/format";

import styles from "./dashboard.module.css";

// Small pieces shared by the dashboard pages (Overview, Performance).

export type Tone = "ok" | "warn" | "error" | undefined;
type Health = components["schemas"]["HealthReport"];

export type Trend = { text: string; tone?: Tone };

export function Kpi({
  label,
  value,
  note,
  tone,
  trend,
}: {
  label: string;
  value: string;
  note: string;
  tone?: Tone;
  trend?: Trend;
}) {
  return (
    <div className={styles.kpi}>
      <p className={styles.kpiLabel}>{label}</p>
      <p className={`${styles.kpiValue} ${tone ? styles[tone] : ""}`}>{value}</p>
      {trend && <p className={`${styles.kpiNote} ${trend.tone ? styles[trend.tone] : ""}`}>{trend.text}</p>}
      <p className={styles.kpiNote}>{note}</p>
    </div>
  );
}

export function Problem({ message }: { message: string }) {
  return (
    <p role="alert" className={styles.error}>
      ✕ {message}
    </p>
  );
}

/** Live GPU memory gauge + loaded models, indexing, uptime (from GET /v1/admin/health). */
export function GpuAndModels({ health }: { health: Health }) {
  const gpu = health.gpu;
  const percent = gpu ? Math.round(Math.min(1, gpu.memory_used_mb / gpu.memory_total_mb) * 100) : 0;

  return (
    <>
      {gpu ? (
        <figure className={styles.gauge}>
          {/* Half circle: grey track, accent arc = share of GPU memory in use */}
          <svg viewBox="0 0 120 66" aria-hidden="true">
            <path d="M 10 60 A 50 50 0 0 1 110 60" pathLength={100} className={styles.gaugeTrack} />
            {percent > 0 && (
              <path
                d="M 10 60 A 50 50 0 0 1 110 60"
                pathLength={100}
                className={styles.gaugeArc}
                strokeDasharray={`${percent} 100`}
              />
            )}
          </svg>
          <figcaption>
            <span className={styles.gaugeValue}>{percent}%</span>
            <span className={styles.kpiNote}>
              {formatMb(gpu.memory_used_mb)} of {formatMb(gpu.memory_total_mb)} in use, {gpu.utilization_pct}% busy
            </span>
          </figcaption>
        </figure>
      ) : (
        <p className={styles.muted}>No GPU reported.</p>
      )}
      <dl className={styles.list}>
        {health.models.length === 0 ? (
          <div>
            <dt>Models</dt>
            <dd className={styles.muted} title="Ollama unloads idle models; they load again on the next question">
              None loaded
            </dd>
          </div>
        ) : (
          health.models.map((m) => (
            <div key={m.name}>
              <dt className="mono">{m.name}</dt>
              <dd>{formatMb(m.vram_mb)}</dd>
            </div>
          ))
        )}
        <div>
          <dt>Indexing</dt>
          <dd>{health.ingest_busy ? "Busy" : "Idle"}</dd>
        </div>
        <div>
          <dt>Service up for</dt>
          <dd>{formatUptime(health.uptime_s)}</dd>
        </div>
      </dl>
    </>
  );
}

export type Share = { key: string; label: string; value: number; text: string; note: string };

/** Horizontal bars, one row per item (label + numbers, then a thin bar); the biggest in the accent color. */
export function ShareBars({ items }: { items: Share[] }) {
  const most = Math.max(1, ...items.map((i) => i.value));

  return (
    <ul className={styles.bars}>
      {items.map((i) => (
        <li key={i.key}>
          <span className={`${styles.barLabel} mono`} translate="no">
            {i.label}
          </span>
          <span className={styles.barValue}>
            {i.text} <span className={styles.kpiNote}>{i.note}</span>
          </span>
          {/* The numbers above carry the meaning; the bar is a visual aid only */}
          <span className={styles.barTrack} aria-hidden="true">
            {i.value > 0 && (
              <span
                className={i.value === most ? styles.barTop : styles.barFill}
                style={{ width: `${(i.value / most) * 100}%` }}
              />
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
