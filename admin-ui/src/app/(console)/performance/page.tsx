import { Suspense } from "react";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatCount, formatDateTime, formatMs, formatPercent, formatTime } from "@/lib/format";

import AutoRefresh from "../auto-refresh";
import styles from "../dashboard.module.css";
import { CardLoading, GpuCard } from "../health-cards";
import { Kpi, Problem, ShareBars, type Trend } from "../widgets";
import { RequestsChart, TimesChart } from "./charts";
import WindowSwitch from "./window-switch";

export const metadata = { title: "Performance" };

// The time window lives in the URL (?window=24h): survives a reload, can be shared.
const WINDOWS = {
  "1h": { label: "1 h", minutes: 60, bucket: 5, bucketLabel: "5 minutes" },
  "24h": { label: "24 h", minutes: 1440, bucket: 60, bucketLabel: "hour" },
  "7d": { label: "7 d", minutes: 10080, bucket: 360, bucketLabel: "6 hours" },
} as const;
type WindowKey = keyof typeof WINDOWS;

// Endpoints shown before the "Show all" fold
const TOP_ROUTES = 5;
// FastAPI's largest metrics window (7 days)
const MAX_WINDOW_MINUTES = 10080;
// The 1 h window refreshes itself (useful while watching a live test)
const REFRESH_SECONDS = 30;

/** "▲ 12% vs previous 24 h". For errors, up is bad (red) and down is good (green). */
function change(now: number, before: number, label: string, upIsBad = false): Trend | undefined {
  if (now === 0 && before === 0) return undefined;
  if (before === 0) return { text: `▲ from 0 in previous ${label}`, tone: upIsBad ? "error" : undefined };
  const percent = Math.round(((now - before) / before) * 100);
  if (percent === 0) return { text: `same as the previous ${label}` };
  const up = percent > 0;
  return {
    text: `${up ? "▲" : "▼"} ${Math.abs(percent)}% vs previous ${label}`,
    tone: upIsBad ? (up ? "error" : "ok") : undefined,
  };
}

type Latency = components["schemas"]["LatencyStats"];
type RouteUsage = components["schemas"]["RouteUsage"];

export default async function PerformancePage({ searchParams }: PageProps<"/performance">) {
  const asked = (await searchParams).window;
  const key: WindowKey = typeof asked === "string" && Object.hasOwn(WINDOWS, asked) ? (asked as WindowKey) : "24h";
  const span = WINDOWS[key];

  // The previous period = (last 2 windows) - (last window). FastAPI allows at most 7 days, so no
  // comparison for the 7 d window.
  const compare = span.minutes * 2 <= MAX_WINDOW_MINUTES;

  // Fast calls only; the slow health check is streamed (GpuCard).
  const [series, summary, doubled] = await Promise.all([
    callApi((api) =>
      api.GET("/v1/admin/metrics/timeseries", {
        params: { query: { window_minutes: span.minutes, bucket_minutes: span.bucket } },
      }),
    ),
    callApi((api) => api.GET("/v1/admin/metrics/summary", { params: { query: { window_minutes: span.minutes } } })),
    compare
      ? callApi((api) =>
          api.GET("/v1/admin/metrics/summary", { params: { query: { window_minutes: span.minutes * 2 } } }),
        )
      : null,
  ]);
  endSessionOn401(series, summary, ...(doubled ? [doubled] : []));

  const tick = key === "7d" ? formatDateTime : (iso: string) => formatTime(iso).slice(0, 5);
  const quiet = summary.ok && summary.data.requests === 0;
  const routes = summary.ok ? [...summary.data.by_route].sort((a, b) => b.requests - a.requests) : [];
  const previous = summary.ok && doubled?.ok ? doubled.data : null;
  // Busiest bucket, per minute (the laptop answered about 17-18 chats per minute at most in Phase 5)
  const peak = series.ok ? Math.max(0, ...series.data.map((p) => p.requests)) / span.bucket : 0;

  return (
    <>
      {key === "1h" && <AutoRefresh seconds={REFRESH_SECONDS} />}
      <header className={styles.header}>
        <h1>Performance</h1>
        {key === "1h" && (
          <p className={styles.muted}>
            Updated {formatTime(new Date())}, refreshes every {REFRESH_SECONDS} s
          </p>
        )}
        <WindowSwitch
          current={key}
          options={(Object.keys(WINDOWS) as WindowKey[]).map((k) => ({ key: k, label: WINDOWS[k].label }))}
        />
      </header>

      {summary.ok ? (
        <section className={styles.kpis} aria-label={`Last ${span.label}`}>
          <Kpi
            label={`Requests, ${span.label}`}
            value={formatCount(summary.data.requests)}
            trend={previous ? change(summary.data.requests, previous.requests - summary.data.requests, span.label) : undefined}
            note={`busiest: ${peak.toFixed(1)} per minute`}
          />
          <Kpi
            label="Errors"
            value={formatCount(summary.data.errors)}
            tone={summary.data.errors > 0 ? "error" : undefined}
            trend={
              previous
                ? change(summary.data.errors, previous.errors - summary.data.errors, span.label, true)
                : undefined
            }
            note={`${formatCount(summary.data.client_errors)} refused (4xx), ${formatCount(summary.data.busy_rejections)} busy`}
          />
          <Kpi
            label="Typical answer time"
            value={formatMs(summary.data.total_ms.p50)}
            note={`p95 ${formatMs(summary.data.total_ms.p95)}`}
          />
          <Kpi
            label="Queue wait (p95)"
            value={formatMs(summary.data.queue_ms.p95)}
            note={`typical ${formatMs(summary.data.queue_ms.p50)}`}
          />
        </section>
      ) : (
        <Problem message={displayMessage(summary.error)} />
      )}

      <div className={styles.pair}>
        <section className={styles.card} aria-labelledby="volume">
          <h2 id="volume">Requests and errors</h2>
          {!series.ok ? (
            <Problem message={displayMessage(series.error)} />
          ) : quiet || series.data.length === 0 ? (
            <p className={styles.muted}>No requests in the last {span.label}.</p>
          ) : (
            <RequestsChart points={series.data} tick={tick} bucket={span.bucketLabel} />
          )}
        </section>

        <section className={styles.card} aria-labelledby="times">
          <h2 id="times">Response time</h2>
          {!series.ok ? (
            <Problem message={displayMessage(series.error)} />
          ) : quiet || series.data.length === 0 ? (
            <p className={styles.muted}>No requests in the last {span.label}.</p>
          ) : (
            <TimesChart points={series.data} tick={tick} />
          )}
        </section>
      </div>

      <div className={styles.columns}>
        {/* Wide column: where the time goes, busiest endpoints */}
        <div className={styles.column}>
          {summary.ok && !quiet && (
            <>
              <section className={styles.card} aria-labelledby="steps">
                <h2 id="steps">Where the time goes</h2>
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th scope="col">Step</th>
                        <th scope="col" className={styles.number}>
                          Typical
                        </th>
                        <th scope="col" className={styles.number}>
                          p95
                        </th>
                        <th scope="col" className={styles.number}>
                          Slowest
                        </th>
                        <th scope="col" className={styles.number}>
                          Measured
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <Step label="Queue wait" stats={summary.data.queue_ms} />
                      <Step label="Search and answer" stats={summary.data.rag_ms} />
                      <Step label="First word (streams)" stats={summary.data.ttft_ms} />
                      <Step label="Whole request" stats={summary.data.total_ms} />
                    </tbody>
                  </table>
                </div>
              </section>

              <section className={styles.card} aria-labelledby="routes">
                <h2 id="routes">Busiest endpoints</h2>
                <RouteTable routes={routes.slice(0, TOP_ROUTES)} />
                {routes.length > TOP_ROUTES && (
                  <details className={styles.more}>
                    <summary>Show all {routes.length} endpoints</summary>
                    <RouteTable routes={routes.slice(TOP_ROUTES)} />
                  </details>
                )}
              </section>
            </>
          )}
        </div>

        {/* Narrow column: answer outcomes, the machine right now, requests by app */}
        <div className={styles.column}>
          {summary.ok && summary.data.chats > 0 && (
            <section className={styles.card} aria-labelledby="outcomes">
              <h2 id="outcomes">Answer outcomes</h2>
              <Outcomes summary={summary.data} />
            </section>
          )}

          {/* key = window: switching windows never waits for the slow GPU reading (it fills in after) */}
          <Suspense key={key} fallback={<CardLoading title="GPU and models, right now" height="13rem" />}>
            <GpuCard title="GPU and models, right now" />
          </Suspense>

          {summary.ok && !quiet && (
            <section className={styles.card} aria-labelledby="apps">
              <h2 id="apps">Requests by app</h2>
              <ShareBars
                items={summary.data.by_app.map((a) => ({
                  key: a.app_id,
                  label: a.app_id,
                  value: a.requests,
                  text: formatCount(a.requests),
                  note: `${formatPercent(a.requests, summary.data.requests)}${a.errors > 0 ? `, ${formatCount(a.errors)} errors` : ""}`,
                }))}
              />
            </section>
          )}
        </div>
      </div>
    </>
  );
}

/** Every chat ends one of four ways; the four always add up to the chat count. */
function Outcomes({ summary }: { summary: components["schemas"]["MetricsSummary"] }) {
  const { chats, answered, refused } = summary;
  const busy = summary.busy_rejections;
  const failed = Math.max(0, chats - answered - refused - busy);
  const parts = [
    { label: "Answered", count: answered, className: styles.outcomeAnswered },
    { label: "“I don’t know”", count: refused, className: styles.outcomeRefused },
    { label: "Busy, try again", count: busy, className: styles.outcomeBusy },
    { label: "Failed", count: failed, className: styles.outcomeFailed },
  ];

  return (
    <>
      <div className={styles.stack} aria-hidden="true">
        {parts.map(
          (p) => p.count > 0 && <span key={p.label} className={p.className} style={{ flexGrow: p.count }} />,
        )}
      </div>
      <dl className={styles.list}>
        {parts.map((p) => (
          <div key={p.label}>
            <dt>
              <i className={`${styles.dot} ${p.className}`} aria-hidden="true" /> {p.label}
            </dt>
            <dd>
              {formatCount(p.count)} <span className={styles.muted}>({formatPercent(p.count, chats)})</span>
            </dd>
          </div>
        ))}
      </dl>
    </>
  );
}

function Step({ label, stats }: { label: string; stats: Latency }) {
  return (
    <tr>
      <td>{label}</td>
      <td className={styles.number}>{formatMs(stats.p50)}</td>
      <td className={styles.number}>{formatMs(stats.p95)}</td>
      <td className={styles.number}>{formatMs(stats.max)}</td>
      <td className={`${styles.number} ${styles.muted}`}>{formatCount(stats.count)}</td>
    </tr>
  );
}

function RouteTable({ routes }: { routes: RouteUsage[] }) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Endpoint</th>
            <th scope="col" className={styles.number}>
              Requests
            </th>
            <th scope="col" className={styles.number}>
              Errors
            </th>
            <th scope="col" className={styles.number}>
              p95
            </th>
          </tr>
        </thead>
        <tbody>
          {routes.map((r) => (
            <tr key={r.route}>
              <td className={`mono ${styles.nowrap}`}>{r.route}</td>
              <td className={styles.number}>{formatCount(r.requests)}</td>
              <td className={`${styles.number} ${r.errors > 0 ? styles.error : ""}`}>{formatCount(r.errors)}</td>
              <td className={styles.number}>{formatMs(r.p95_ms)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
