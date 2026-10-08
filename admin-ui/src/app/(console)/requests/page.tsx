import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatCount, formatMs, formatStamp } from "@/lib/format";

import styles from "../dashboard.module.css";
import { Problem } from "../widgets";

export const metadata = { title: "Request log" };

const PAGE_SIZE = 100;

type Row = components["schemas"]["RequestLogOut"];

export default async function RequestLogPage({ searchParams }: PageProps<"/requests">) {
  const params = await searchParams;
  const one = (v: string | string[] | undefined) => (typeof v === "string" ? v.trim() : "");
  const app = one(params.app);
  const user = one(params.user);
  const errorsOnly = one(params.errors) === "1";
  const page = Math.max(1, Number.parseInt(one(params.page), 10) || 1);

  const [rows, apps] = await Promise.all([
    callApi((api) =>
      api.GET("/v1/admin/requests", {
        params: {
          query: {
            app_id: app || undefined,
            user_id: user || undefined,
            errors_only: errorsOnly,
            limit: PAGE_SIZE,
            offset: (page - 1) * PAGE_SIZE,
          },
        },
      }),
    ),
    callApi((api) => api.GET("/v1/admin/apps")),
  ]);
  endSessionOn401(rows, apps);

  // Same filters, another page (Previous / Next keep the filters)
  const pageHref = (p: number) => {
    const q = new URLSearchParams();
    if (app) q.set("app", app);
    if (user) q.set("user", user);
    if (errorsOnly) q.set("errors", "1");
    if (p > 1) q.set("page", String(p));
    const s = q.toString();
    return s ? `/requests?${s}` : "/requests";
  };
  const filtered = Boolean(app || user || errorsOnly);

  return (
    <>
      <header className={styles.header}>
        <h1>Request log</h1>
        <p className={styles.muted}>Newest first, {PAGE_SIZE} per page</p>
      </header>

      {/* A plain GET form: the filters land in the URL (shareable, Back works), no JavaScript */}
      <form action="/requests" className={styles.filters}>
        <label>
          <span>App</span>
          <select name="app" defaultValue={app}>
            <option value="">All apps</option>
            {apps.ok &&
              apps.data.map((a) => (
                <option key={a.app_id} value={a.app_id}>
                  {a.display_name ? `${a.display_name} (${a.app_id})` : a.app_id}
                </option>
              ))}
          </select>
        </label>
        <label>
          <span>User id</span>
          <input
            name="user"
            defaultValue={user}
            placeholder="e.g. 1042…"
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        <label className={styles.check}>
          <input type="checkbox" name="errors" value="1" defaultChecked={errorsOnly} />
          <span>Errors only</span>
        </label>
        <button type="submit" className={styles.apply}>
          Apply filters
        </button>
        {filtered && (
          <Link href="/requests" className={styles.clear}>
            Clear filters
          </Link>
        )}
      </form>

      <section className={styles.card} aria-label="Requests">
        {!rows.ok ? (
          <Problem message={displayMessage(rows.error)} />
        ) : rows.data.length === 0 ? (
          <p className={styles.muted}>
            {page > 1 ? "No more requests." : filtered ? "No requests match these filters." : "No requests yet."}
          </p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Request</th>
                  <th scope="col">Result</th>
                  <th scope="col">App / user</th>
                  <th scope="col" className={styles.number}>
                    Total
                  </th>
                  <th scope="col" className={styles.number}>
                    Queue
                  </th>
                  <th scope="col" className={styles.number}>
                    Model
                  </th>
                  <th scope="col">Answer</th>
                </tr>
              </thead>
              <tbody>
                {rows.data.map((r) => (
                  <RequestRow key={r.request_id} row={r} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {rows.ok && (page > 1 || rows.data.length === PAGE_SIZE) && (
        <nav aria-label="Pages" className={styles.pager}>
          {page > 1 ? <Link href={pageHref(page - 1)}>← Previous</Link> : <span />}
          {rows.data.length > 0 ? (
            <span className={styles.muted}>
              Rows {formatCount((page - 1) * PAGE_SIZE + 1)}–{formatCount((page - 1) * PAGE_SIZE + rows.data.length)}
            </span>
          ) : (
            <span />
          )}
          {/* ponytail: the API gives no total, so "Next" shows whenever this page is full */}
          {rows.data.length === PAGE_SIZE ? <Link href={pageHref(page + 1)}>Next →</Link> : <span />}
        </nav>
      )}
    </>
  );
}

function RequestRow({ row }: { row: Row }) {
  const failed = row.status >= 400 || row.error_code !== null;
  // A chat request links to its conversation (the thread page arrives in 6B.3 sub-step 3)
  const thread =
    row.conversation_id && row.app_id && row.user_id
      ? `/users/${encodeURIComponent(row.app_id)}/${encodeURIComponent(row.user_id)}/${encodeURIComponent(row.conversation_id)}`
      : null;

  return (
    <tr id={row.request_id}>
      <td className={styles.nowrap} title={row.request_id}>
        {formatStamp(row.created_at)}
      </td>
      <td className={`mono ${styles.nowrap}`}>
        {row.method} {row.route ?? row.path}
        {row.collection && <span className={styles.muted}> ({row.collection})</span>}
      </td>
      <td className={styles.nowrap}>
        <span className={failed ? styles.error : styles.muted}>{row.status}</span>
        {row.error_code && <span className="mono"> {row.error_code}</span>}
      </td>
      <td className={styles.nowrap}>
        <span className="mono" translate="no">
          {row.app_id ?? "–"}
        </span>
        {row.user_id && (
          <span className={styles.muted}>
            {" "}
            / {row.user_id}
            {row.user_role && ` (${row.user_role})`}
          </span>
        )}
      </td>
      <td className={styles.number}>{formatMs(row.duration_ms)}</td>
      <td className={styles.number}>{formatMs(row.queue_ms)}</td>
      <td className={styles.number}>{formatMs(row.rag_ms)}</td>
      <td className={styles.nowrap}>
        {row.found === true && <span className={styles.ok}>● Answered</span>}
        {row.found === false && <span className={styles.muted}>○ “I don’t know”</span>}
        {thread && (
          <>
            {" "}
            <Link href={thread}>Open chat</Link>
          </>
        )}
      </td>
    </tr>
  );
}
