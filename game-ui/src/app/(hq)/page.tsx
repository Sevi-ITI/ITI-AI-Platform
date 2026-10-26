// Copied from admin-ui src/app/(console)/page.tsx (G3). Same FastAPI calls and data; the panel header shows the title.
import Link from "next/link";
import { Suspense } from "react";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatCount, formatDateTime, formatMb, formatMs, formatPercent, formatTime, formatUptime } from "@/lib/format";
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import AutoRefresh from "./kit/auto-refresh";
import styles from "./kit/dashboard.module.css";
import { CardLoading, currentHealth } from "./kit/health-cards";
import { StatusErrorIcon, StatusOkIcon, StatusWarnIcon } from "./kit/icons";
import { Kpi, Problem, ShareBars, type Tone } from "./kit/widgets";

export const metadata = { title: "Overview" };

type Health = components["schemas"]["HealthReport"];

const REFRESH_SECONDS = 30;

export default async function OverviewPage() {
  await testersGoToChat(); // testers have only the Chat page
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
        {/* Wide column: the system (status, GPU, models), then the latest refused / failed requests */}
        <div className={styles.column}>
          <Suspense fallback={<CardLoading title="System" height="9rem" />}>
            <StatusCard />
          </Suspense>

          {/* Refused (4xx, amber) and failed (5xx, red): the Errors number above counts only the failed ones */}
          <section className={styles.card} aria-labelledby="errors">
            <div className={styles.cardHead}>
              <h2 id="errors">Latest refused or failed</h2>
              <Link href="/requests?errors=1" className={styles.smallButton}>
                All in Request log →
              </Link>
            </div>
            {!errors.ok ? (
              <Problem message={displayMessage(errors.error)} />
            ) : errors.data.length === 0 ? (
              <p className={styles.muted}>No refused or failed requests in the log.</p>
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
                      // Full detail (app, user, request id) lives on the Request log page: the time links to its row.
                      <tr key={row.request_id} title={`${row.request_id}, ${row.app_id ?? "no app"}`}>
                        <td className={styles.nowrap}>
                          <Link href={`/requests?errors=1#${encodeURIComponent(row.request_id)}`}>
                            {formatDateTime(row.created_at)}
                          </Link>
                        </td>
                        <td className={`mono ${styles.wrapAnywhere}`}>
                          {row.method} {row.route ?? row.path}
                        </td>
                        <td className={styles.nowrap}>
                          <span className={row.status >= 500 ? styles.error : styles.warn}>
                            {row.status >= 500 ? "✕" : "▲"} {row.status}
                          </span>{" "}
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

        {/* Narrow column: collections */}
        <div className={styles.column}>
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
                  note: `${c.chunks === 1 ? "chunk" : "chunks"}, ${formatCount(c.documents)} ${c.documents === 1 ? "doc" : "docs"}`,
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
      {health.ok ? (
        <Status health={health.data} />
      ) : (
        <>
          <h2 id="status">System</h2>
          <Problem message={displayMessage(health.error)} />
        </>
      )}
    </section>
  );
}

// One card for the machine: the overall state as a pill, four tiles (database, Ollama, answer queue, GPU memory),
// then the loaded models, indexing and uptime on one line. (Was two cards with a large GPU gauge.)
function Status({ health }: { health: Health }) {
  const problems = [
    !health.database.ok && "the database is not reachable",
    !health.ollama.ok && "Ollama is not reachable",
  ].filter(Boolean);
  const queue = health.llm_slots;
  const gpu = health.gpu;
  const gpuPercent = gpu ? Math.round(Math.min(1, gpu.memory_used_mb / gpu.memory_total_mb) * 100) : null;

  return (
    <>
      <div className={styles.cardHead}>
        <h2 id="status">System</h2>
        {health.status === "ok" ? (
          <p className={`${styles.statusPill} ${styles.statusPill_ok}`}>
            <StatusOkIcon /> Everything is working
          </p>
        ) : (
          <p className={`${styles.statusPill} ${styles.statusPill_error}`}>
            <StatusErrorIcon /> Degraded{problems.length ? `: ${problems.join(" and ")}` : ""}
          </p>
        )}
      </div>
      <div className={styles.tiles}>
        <Tile
          label="Database"
          tone={health.database.ok ? "ok" : "error"}
          value={health.database.ok ? "OK" : "Not reachable"}
          note={health.database.ok ? formatMs(health.database.latency_ms) : health.database.detail}
        />
        <Tile
          label="Ollama"
          tone={health.ollama.ok ? "ok" : "error"}
          value={health.ollama.ok ? "OK" : "Not reachable"}
          note={health.ollama.ok ? formatMs(health.ollama.latency_ms) : health.ollama.detail}
        />
        <Tile
          label="Answer queue"
          tone={queue.waiting > 0 ? "warn" : "ok"}
          value={`${queue.running} of ${queue.limit}`}
          note={`running, ${queue.waiting} waiting`}
        />
        <Tile
          label="GPU memory"
          tone={gpuPercent === null ? undefined : gpuPercent >= 90 ? "warn" : "ok"}
          value={gpuPercent === null ? "–" : `${gpuPercent}%`}
          note={
            gpu
              ? `${formatMb(gpu.memory_used_mb)} of ${formatMb(gpu.memory_total_mb)}, ${gpu.utilization_pct}% busy`
              : "No GPU reported"
          }
        />
      </div>
      <dl className={styles.facts}>
        <div>
          <dt>Models</dt>
          {health.models.length === 0 ? (
            <dd title="Ollama unloads idle models; they load again on the next question">None loaded</dd>
          ) : (
            <dd>
              {health.models.map((m, i) => (
                <span key={m.name}>
                  {i > 0 && ", "}
                  <span className="mono">{m.name}</span> ({formatMb(m.vram_mb)})
                </span>
              ))}
            </dd>
          )}
        </div>
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

// The shape of the icon and the word carry the state; the tile's colored underline repeats it.
function Tile({ label, value, note, tone }: { label: string; value: string; note: string; tone: Tone }) {
  const Icon = tone === "ok" ? StatusOkIcon : tone === "warn" ? StatusWarnIcon : tone === "error" ? StatusErrorIcon : null;
  return (
    <div className={`${styles.tile} ${tone ? styles[`tile_${tone}`] : ""}`}>
      <p className={styles.kpiLabel}>{label}</p>
      <p className={`${styles.tileValue} ${tone ? styles[tone] : ""}`}>
        {Icon && <Icon />} {value}
      </p>
      <p className={styles.kpiNote}>{note}</p>
    </div>
  );
}
