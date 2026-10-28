// Users & chats, decluttered for game-ui like Apps & keys and Companies (Vince, 2026-10-28). Not a copy of admin-ui's
// page any more: the same FastAPI calls (check:parity), a calmer layout: a one-line summary with the filters beside
// it, then one line per user (who and their role | where they chat | how much | when) instead of a five-column table.
import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import { formatCount, formatDateTime, initials } from "@/lib/format";
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import Pager from "../kit/pager";
import styles from "../kit/dashboard.module.css";
import { Problem } from "../kit/widgets";
import css from "./users.module.css";

export const metadata = { title: "Users & chats" };

const PAGE_SIZE = 100;

// Every app's users (the C# apps' users and console people), most recently active first, optionally one app's and /
// or one company's (?app=, ?company=: in the URL, shareable, Back works). A line opens that user's conversations.
export default async function UsersPage({ searchParams }: PageProps<"/users">) {
  await testersGoToChat(); // testers have only the Chat page
  const params = await searchParams;
  const one = (v: string | string[] | undefined) => (typeof v === "string" ? v.trim() : "");
  const app = one(params.app);
  const company = one(params.company);
  const page = Math.max(1, Number.parseInt(one(params.page), 10) || 1);

  const [users, apps, companies] = await Promise.all([
    callApi((api) =>
      api.GET("/v1/admin/users", {
        params: {
          query: {
            app_id: app || undefined,
            company_id: company || undefined,
            limit: PAGE_SIZE,
            offset: (page - 1) * PAGE_SIZE,
          },
        },
      }),
    ),
    callApi((api) => api.GET("/v1/admin/apps")),
    callApi((api) => api.GET("/v1/admin/companies")),
  ]);
  endSessionOn401(users, apps, companies);
  const companyNames = new Map((companies.ok ? companies.data : []).map((c) => [c.company_id, c.name]));
  const appNames = new Map((apps.ok ? apps.data : []).map((a) => [a.app_id, a.display_name ?? a.app_id]));

  // Same filter, another page
  const pageHref = (p: number) => {
    const q = new URLSearchParams();
    if (app) q.set("app", app);
    if (company) q.set("company", company);
    if (p > 1) q.set("page", String(p));
    const s = q.toString();
    return s ? `/users?${s}` : "/users";
  };

  return (
    <>
      {/* summary on the left, the filters on the right (a plain GET form: no JavaScript) */}
      <div className={css.top}>
        <p className={styles.muted}>
          {users.ok ? `${formatCount(users.data.length)}${users.data.length === PAGE_SIZE ? "+" : ""} users` : ""} | most
          recently active first
        </p>
        <form action="/users" className={css.filters}>
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
          <button type="submit" className={styles.filterApply}>
            Filter
          </button>
          {(app || company) && (
            <Link href="/users" className={styles.clear}>
              Clear
            </Link>
          )}
        </form>
      </div>

      {!users.ok ? (
        <Problem message={displayMessage(users.error)} />
      ) : users.data.length === 0 ? (
        <p className={styles.muted}>
          {page > 1
            ? "No more users."
            : app || company
              ? "No one here has chatted yet."
              : "No one has chatted yet. Users appear here after their first question."}
        </p>
      ) : (
        <section className={`${styles.card} ${css.list}`} aria-label="Users">
          <ul className={css.rows}>
            {users.data.map((u) => {
              const href = `/users/${encodeURIComponent(u.app_id)}/${encodeURIComponent(u.user_id)}?company=${encodeURIComponent(u.company_id)}`;
              return (
                <li key={`${u.app_id}/${u.company_id}/${u.user_id}`} className={css.row}>
                  <span className={styles.appAvatar} aria-hidden="true">
                    {initials(u.user_id)}
                  </span>
                  <div className={css.who}>
                    <Link href={href} className={`mono ${css.userLink}`} translate="no">
                      {u.user_id}
                    </Link>
                    {u.user_role && <span className={styles.kpiNote}>{u.user_role}</span>}
                  </div>
                  <span className={css.where}>
                    {companyNames.get(u.company_id) ?? u.company_id} | {appNames.get(u.app_id) ?? u.app_id}
                  </span>
                  <span className={css.counts}>
                    <b>{formatCount(u.conversations)}</b> {u.conversations === 1 ? "chat" : "chats"} |{" "}
                    <b>{formatCount(u.messages)}</b> {u.messages === 1 ? "message" : "messages"}
                  </span>
                  <span className={css.when}>{u.last_active ? formatDateTime(u.last_active) : "–"}</span>
                </li>
              );
            })}
          </ul>
          {(page > 1 || users.data.length === PAGE_SIZE) && (
            <Pager page={page} count={users.data.length} pageSize={PAGE_SIZE} noun="Users" href={pageHref} />
          )}
        </section>
      )}
    </>
  );
}
