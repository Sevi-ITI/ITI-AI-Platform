// Request log, decluttered for game-ui like the other rooms (Vince, 2026-10-28). Not a copy of admin-ui's page any
// more: the same FastAPI calls (check:parity), a calmer list: a one-line summary with the filters on one row at the
// right, the requests grouped by day, one line per request (time | request | result | who | how long) instead of a
// five-column table. Clicking a line opens every detail in the panel beside it (?req=, as before).
import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { dayKey, formatDay, formatMs, formatStamp, formatTime } from "@/lib/format";
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import CopyButton from "../kit/copy-button";
import styles from "../kit/dashboard.module.css";
import FocusOnOpen from "../kit/focus-on-open";
import { StatusErrorIcon, StatusOkIcon, StatusWarnIcon } from "../kit/icons";
import Pager from "../kit/pager";
import { Problem } from "../kit/widgets";
import css from "./requests.module.css";

export const metadata = { title: "Request log" };

const PAGE_SIZE = 100;

type Row = components["schemas"]["RequestLogOut"];

// The request log, newest first. Clicking a line opens every detail of that request in a side panel. The open row
// lives in the URL (?req=<request id>) like the filters: it survives a reload, can be shared, and Back closes it.
export default async function RequestLogPage({ searchParams }: PageProps<"/requests">) {
  await testersGoToChat(); // testers have only the Chat page
  const params = await searchParams;
  const one = (v: string | string[] | undefined) => (typeof v === "string" ? v.trim() : "");
  const app = one(params.app);
  const company = one(params.company);
  const user = one(params.user);
  const errorsOnly = one(params.errors) === "1";
  const page = Math.max(1, Number.parseInt(one(params.page), 10) || 1);
  const req = one(params.req);

  const [rows, apps, companies] = await Promise.all([
    callApi((api) =>
      api.GET("/v1/admin/requests", {
        params: {
          query: {
            app_id: app || undefined,
            company_id: company || undefined,
            user_id: user || undefined,
            errors_only: errorsOnly,
            limit: PAGE_SIZE,
            offset: (page - 1) * PAGE_SIZE,
          },
        },
      }),
    ),
    callApi((api) => api.GET("/v1/admin/apps")),
    callApi((api) => api.GET("/v1/admin/companies")),
  ]);
  endSessionOn401(rows, apps, companies);
  const companyNames = new Map((companies.ok ? companies.data : []).map((c) => [c.company_id, c.name]));

  // Same filters, another page or another open row (Previous / Next and the panel keep the filters)
  const href = ({ p = page, open = "" }: { p?: number; open?: string }) => {
    const q = new URLSearchParams();
    if (app) q.set("app", app);
    if (company) q.set("company", company);
    if (user) q.set("user", user);
    if (errorsOnly) q.set("errors", "1");
    if (p > 1) q.set("page", String(p));
    if (open) q.set("req", open);
    const s = q.toString();
    return s ? `/requests?${s}` : "/requests";
  };
  const filtered = Boolean(app || company || user || errorsOnly);
  const selected = req && rows.ok ? (rows.data.find((r) => r.request_id === req) ?? null) : null;

  // The rows by day (newest first, as they come), each day under its own small heading
  const days: { key: string; label: string; rows: Row[] }[] = [];
  for (const r of rows.ok ? rows.data : []) {
    const key = dayKey(r.created_at);
    if (days.at(-1)?.key !== key) days.push({ key, label: formatDay(r.created_at), rows: [] });
    days.at(-1)!.rows.push(r);
  }
  const refused = rows.ok ? rows.data.filter((r) => r.status >= 400).length : 0;

  return (
    <>
      {/* summary on the left, the filters on one row at the right (a plain GET form: no JavaScript) */}
      <div className={css.top}>
        <p className={styles.muted}>
          {rows.ok ? `${rows.data.length}${rows.data.length === PAGE_SIZE ? "+" : ""} requests` : ""}
          {refused > 0 && <span className={styles.warn}> | {refused} refused or failed</span>} | newest first | click
          one for every detail
        </p>
        <form action="/requests" className={css.filters}>
          <label>
            <span className="sr-only">App</span>
            <select name="app" defaultValue={app}>
              <option value="">All apps</option>
              {apps.ok &&
                apps.data.map((a) => (
                  <option key={a.app_id} value={a.app_id}>
                    {a.display_name ?? a.app_id}
                  </option>
                ))}
            </select>
          </label>
          <label>
            <span className="sr-only">Company</span>
            <select name="company" defaultValue={company}>
              <option value="">All companies</option>
              {companies.ok &&
                companies.data.map((c) => (
                  <option key={c.company_id} value={c.company_id}>
                    {c.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            <span className="sr-only">User id</span>
            <input name="user" defaultValue={user} placeholder="User id…" autoComplete="off" spellCheck={false} />
          </label>
          <label className={css.check}>
            <input type="checkbox" name="errors" value="1" defaultChecked={errorsOnly} />
            <span>Refused or failed only</span>
          </label>
          <button type="submit" className={styles.filterApply}>
            Filter
          </button>
          {filtered && (
            <Link href="/requests" className={styles.clear}>
              Clear
            </Link>
          )}
        </form>
      </div>

      <div className={req ? styles.split : undefined}>
        <section className={`${styles.card} ${css.list}`} aria-label="Requests">
          {!rows.ok ? (
            <Problem message={displayMessage(rows.error)} />
          ) : rows.data.length === 0 ? (
            <p className={styles.muted}>
              {page > 1 ? "No more requests." : filtered ? "No requests match these filters." : "No requests yet."}
            </p>
          ) : (
            <>
              {days.map((d) => (
                <div key={d.key} className={css.day}>
                  <h2 className={css.dayTitle}>
                    {d.label} <span className={css.dayCount}>{d.rows.length}</span>
                  </h2>
                  <ul className={css.rows}>
                    {d.rows.map((r) => (
                      <RequestRow
                        key={r.request_id}
                        row={r}
                        open={r.request_id === req}
                        openHref={href({ open: r.request_id })}
                        companyNames={companyNames}
                      />
                    ))}
                  </ul>
                </div>
              ))}
              {(page > 1 || rows.data.length === PAGE_SIZE) && (
                <Pager page={page} count={rows.data.length} pageSize={PAGE_SIZE} noun="Rows" href={(p) => href({ p })} />
              )}
            </>
          )}
        </section>

        {req && (
          <DetailPanel
            key={req}
            row={selected}
            req={req}
            closeHref={href({})}
            companyName={selected?.company_id ? companyNames.get(selected.company_id) : undefined}
          />
        )}
      </div>
    </>
  );
}

/** 5xx = failed (red cross), 4xx = refused (amber triangle), else the answer's outcome. Shape + words, color repeats. */
function Result({ row }: { row: Row }) {
  if (row.status >= 500) {
    return (
      <span className={`${styles.withIcon} ${styles.error}`}>
        <StatusErrorIcon /> {row.status} <span className="mono">{row.error_code ?? ""}</span>
      </span>
    );
  }
  if (row.status >= 400) {
    return (
      <span className={`${styles.withIcon} ${styles.warn}`}>
        <StatusWarnIcon /> {row.status} <span className="mono">{row.error_code ?? ""}</span>
      </span>
    );
  }
  if (row.found === true) {
    return (
      <span className={`${styles.withIcon} ${styles.ok}`}>
        <StatusOkIcon /> {row.tools ? "Answered from records" : "Answered"}
      </span>
    );
  }
  if (row.found === false) {
    return <span className={styles.muted}>○ {row.tools ? "Records: nothing found" : "“I don’t know”"}</span>;
  }
  return <span className={styles.muted}>{row.status}</span>;
}

/** One request on one line, the whole line a link that opens its details: time | request | result | who | how long. */
function RequestRow({
  row,
  open,
  openHref,
  companyNames,
}: {
  row: Row;
  open: boolean;
  openHref: string;
  companyNames: Map<string, string>;
}) {
  const who = [
    row.app_id,
    row.company_id && (companyNames.get(row.company_id) ?? row.company_id),
    row.user_id,
  ].filter(Boolean);
  return (
    <li id={row.request_id}>
      {/* scroll={false}: the list stays where it was; the panel opens beside it */}
      <Link
        href={openHref}
        scroll={false}
        className={css.row}
        aria-current={open ? "true" : undefined}
        title={`${formatStamp(row.created_at)} | ${row.request_id}`}
      >
        <span className={css.time}>{formatTime(row.created_at)}</span>
        <span className={`mono ${css.request}`}>
          {row.method} {row.route ?? row.path}
          {row.collection && <span className={css.collection}> {row.collection}</span>}
        </span>
        <span className={css.result}>
          <Result row={row} />
        </span>
        <span className={css.who} translate="no">
          {who.length ? who.join(" | ") : "–"}
        </span>
        <span className={css.duration}>{formatMs(row.duration_ms)}</span>
      </Link>
    </li>
  );
}

/** Every field of one request. Wide windows: a panel beside the list that stays in view; narrow: a floating sheet. */
function DetailPanel({
  row,
  req,
  closeHref,
  companyName,
}: {
  row: Row | null;
  req: string;
  closeHref: string;
  companyName: string | undefined;
}) {
  const thread =
    row?.conversation_id && row.app_id && row.user_id
      ? `/users/${encodeURIComponent(row.app_id)}/${encodeURIComponent(row.user_id)}/${encodeURIComponent(row.conversation_id)}?company=${encodeURIComponent(row.company_id ?? "iti")}`
      : null;

  return (
    <aside className={styles.detailPanel} aria-labelledby="detail-title">
      <div className={styles.cardHead}>
        {/* focused when the panel opens (FocusOnOpen), so keyboard and screen reader users land in it */}
        <h2 id="detail-title" tabIndex={-1}>
          Request details
        </h2>
        <FocusOnOpen targetId="detail-title" />
        <Link href={closeHref} scroll={false} className={styles.smallButton} aria-label="Close the details">
          Close ✕
        </Link>
      </div>

      {!row ? (
        <p className={styles.muted}>
          Request <span className="mono">{req}</span> isn&apos;t on this page (other filters or another page).
        </p>
      ) : (
        <>
          {/* the outcome in words, when there is one beyond the status code below */}
          {(row.status >= 400 || row.found !== null) && (
            <p>
              <Result row={row} />
            </p>
          )}
          <dl className={styles.detailList}>
            <div>
              <dt>Request id</dt>
              <dd className={styles.withIcon}>
                <span className="mono">{row.request_id}</span>
                <CopyButton value={row.request_id} label="request id" />
              </dd>
            </div>
            <div>
              <dt>Time</dt>
              <dd>{formatStamp(row.created_at)}</dd>
            </div>
            <div>
              <dt>Request</dt>
              <dd className={`mono ${styles.wrapAnywhere}`}>
                {row.method} {row.path}
                {row.route && row.route !== row.path && <div className={styles.muted}>route {row.route}</div>}
              </dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>
                {row.status}
                {row.error_code && <span className="mono"> {row.error_code}</span>}
              </dd>
            </div>
            <div>
              <dt>App</dt>
              <dd className="mono">{row.app_id ?? "–"}</dd>
            </div>
            <div>
              <dt>Company</dt>
              <dd>
                {row.company_id ? (
                  <>
                    {companyName ?? row.company_id} <span className={`mono ${styles.muted}`}>{row.company_id}</span>
                  </>
                ) : (
                  "–"
                )}
              </dd>
            </div>
            <div>
              <dt>User</dt>
              <dd>
                {row.user_id ?? "–"}
                {row.user_role && <span className={styles.muted}> ({row.user_role})</span>}
              </dd>
            </div>
            {row.collection && (
              <div>
                <dt>Collection</dt>
                <dd className="mono">{row.collection}</dd>
              </div>
            )}
            {row.reason && (
              <div>
                <dt>Outcome</dt>
                <dd className="mono">{row.reason}</dd>
              </div>
            )}
          </dl>

          <h3 className={styles.detailHeading}>Time spent</h3>
          <dl className={styles.detailList}>
            <div>
              <dt>Whole request</dt>
              <dd className={styles.num}>{formatMs(row.duration_ms)}</dd>
            </div>
            <div>
              <dt>Queue wait</dt>
              <dd className={styles.num}>{formatMs(row.queue_ms)}</dd>
            </div>
            <div>
              <dt>Search and answer</dt>
              <dd className={styles.num}>{formatMs(row.rag_ms)}</dd>
            </div>
            <div>
              <dt>First word</dt>
              <dd className={styles.num}>{formatMs(row.ttft_ms)}</dd>
            </div>
            {row.tokens !== null && (
              <div>
                <dt>Tokens</dt>
                <dd className={styles.num}>{row.tokens}</dd>
              </div>
            )}
          </dl>

          {row.tools && (
            <>
              <h3 className={styles.detailHeading}>Tools the model ran</h3>
              {/* names and time only, never the values (Phase 8) */}
              <p className={`mono ${styles.wrapAnywhere}`} translate="no">
                {row.tools.replaceAll(",", ", ")}
              </p>
              <p className={styles.muted}>{formatMs(row.tools_ms ?? null)} in tools</p>
            </>
          )}

          {thread && (
            <p>
              <Link href={thread}>Open this chat →</Link>
            </p>
          )}
        </>
      )}
    </aside>
  );
}
