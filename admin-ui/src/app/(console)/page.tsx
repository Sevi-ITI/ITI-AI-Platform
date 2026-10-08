import { Suspense } from "react";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatCount, formatDateTime, formatMs, formatPercent, formatTime } from "@/lib/format";

import AutoRefresh from "./auto-refresh";
import styles from "./dashboard.module.css";
import { CardLoading, currentHealth, GpuCard } from "./health-cards";
import { Kpi, Problem, ShareBars, type Tone } from "./widgets";

export const metadata = { title: "Overview" };

type Health = components["schemas"]["HealthReport"];

const REFRESH_SECONDS = 30;

export default async function OverviewPage() {
  // Fast calls only (~20 ms each); the slow health check is streamed (StatusCard, GpuCard).
  const [summary, errors, collections] = await Promise.all([
    callApi((api) => api.GET("/v1/admin/metrics/summary", { params: { query: { window_minutes: 1440 } } })),
    callApi((api) => api.GET("/v1/admin/requests", { params: { query: { errors_only: true, limit: 5 } } })),
    callApi((api) => api.GET("/v1/admin/collections")),
  ]);
  endSessionOn401(summary, errors, collections);

  return (
    <>
      <AutoRefresh seconds={REFRESH_SECONDS} />
      <header className={styles.header}>
        <h1>Overview</h1>
        <p className={styles.muted}>
          Updated {formatTime(new Date())}, refreshes every {REFRESH_SECONDS} s
        </p>
      </header>

      {/* Row 1: the last 24 hours in four numbers */}
      {summary.ok ? (
        <section className={styles.kpis} aria-label="Last 24 hours">
          <Kpi
            label="Requests, 24 h"
            value={formatCount(summary.data.requests)}
            note={`${formatCount(summary.data.client_errors)} refused (4xx)`}
          />
          <Kpi
            label="Chats answered"
            value={formatPercent(summary.data.answered, summary.data.chats)}
            note={`${formatCount(summary.data.chats)} chats, ${formatCount(summary.data.refused)} “I don’t know”`}
          />
          <Kpi
            label="Errors"
            value={formatCount(summary.data.errors)}
            tone={summary.data.errors > 0 ? "error" : undefined}
            note={`${formatCount(summary.data.busy_rejections)} busy (llm_busy)`}
          />
          <Kpi
            label="Typical answer time"
            value={formatMs(summary.data.total_ms.p50)}
            note={`slowest ${formatMs(summary.data.total_ms.max)}`}
          />
        </section>
      ) : (
        <Problem message={displayMessage(summary.error)} />
      )}

      <div className={styles.columns}>
        {/* Wide column: status, then the latest errors */}
        <div className={styles.column}>
          <Suspense fallback={<CardLoading title="System status" height="7rem" />}>
            <StatusCard />
          </Suspense>

          <section className={styles.card} aria-labelledby="errors">
            <h2 id="errors">Latest errors</h2>
            {!errors.ok ? (
              <Problem message={displayMessage(errors.error)} />
            ) : errors.data.length === 0 ? (
              <p className={styles.muted}>No errors in the request log.</p>
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th scope="col">Time</th>
                      <th scope="col">Request</th>
                      <th scope="col">Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {errors.data.map((row) => (
                      // Full detail (app, user, request id) lives on the Request log page (6B.3).
                      <tr key={row.request_id} title={`${row.request_id}, ${row.app_id ?? "no app"}`}>
                        <td className={styles.nowrap}>{formatDateTime(row.created_at)}</td>
                        <td className={`mono ${styles.nowrap}`}>
                          {row.method} {row.route ?? row.path}
                        </td>
                        <td className={styles.nowrap}>
                          <span className={styles.error}>{row.status}</span>{" "}
                          <span className="mono">{row.error_code ?? ""}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>

        {/* Narrow column: GPU and models, collections */}
        <div className={styles.column}>
          <Suspense fallback={<CardLoading title="GPU and models" height="13rem" />}>
            <GpuCard title="GPU and models" />
          </Suspense>

          <section className={styles.card} aria-labelledby="collections">
            <h2 id="collections">Chunks per collection</h2>
            {!collections.ok ? (
              <Problem message={displayMessage(collections.error)} />
            ) : collections.data.length === 0 ? (
              <p className={styles.muted}>No collections configured (ITI_COLLECTIONS in backend\.env).</p>
            ) : (
              <ShareBars
                items={collections.data.map((c) => ({
                  key: c.name,
                  label: c.name,
                  value: c.chunks,
                  text: formatCount(c.chunks),
                  note: `chunks, ${formatCount(c.documents)} docs`,
                }))}
              />
            )}
          </section>
        </div>
      </div>
    </>
  );
}

async function StatusCard() {
  const health = await currentHealth();
  endSessionOn401(health);

  return (
    <section className={styles.card} aria-labelledby="status">
      {health.ok ? <Status health={health.data} /> : <Problem message={displayMessage(health.error)} />}
    </section>
  );
}

function Status({ health }: { health: Health }) {
  const problems = [
    !health.database.ok && "the database is not reachable",
    !health.ollama.ok && "Ollama is not reachable",
  ].filter(Boolean);
  const queue = health.llm_slots;

  return (
    <>
      <h2 id="status" className={health.status === "ok" ? styles.ok : styles.warn}>
        {health.status === "ok"
          ? "● Everything is working"
          : `▲ Degraded${problems.length ? `: ${problems.join(" and ")}` : ""}`}
      </h2>
      <div className={styles.tiles}>
        <Tile
          label="Database"
          tone={health.database.ok ? "ok" : "error"}
          value={health.database.ok ? "● OK" : "✕ Not reachable"}
          note={health.database.ok ? formatMs(health.database.latency_ms) : health.database.detail}
        />
        <Tile
          label="Ollama"
          tone={health.ollama.ok ? "ok" : "error"}
          value={health.ollama.ok ? "● OK" : "✕ Not reachable"}
          note={health.ollama.ok ? formatMs(health.ollama.latency_ms) : health.ollama.detail}
        />
        <Tile
          label="Answer queue"
          tone={queue.waiting > 0 ? "warn" : "ok"}
          value={`${queue.running} of ${queue.limit}`}
          note={`running, ${queue.waiting} waiting`}
        />
      </div>
    </>
  );
}

function Tile({ label, value, note, tone }: { label: string; value: string; note: string; tone: Tone }) {
  return (
    <div className={`${styles.tile} ${tone ? styles[`tile_${tone}`] : ""}`}>
      <p className={styles.kpiLabel}>{label}</p>
      <p className={`${styles.tileValue} ${tone ? styles[tone] : ""}`}>{value}</p>
      <p className={styles.kpiNote}>{note}</p>
    </div>
  );
}
