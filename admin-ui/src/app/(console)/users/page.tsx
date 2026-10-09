import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import { formatCount, formatDateTime } from "@/lib/format";

import Pager from "../pager";
import styles from "../dashboard.module.css";
import { Problem } from "../widgets";

export const metadata = { title: "Users & chats" };

const PAGE_SIZE = 100;

// Every app's users (the C# apps' users and console people), most recently active first, optionally one
// app's (?app=, in the URL like the Request log's filters). A row opens that user's conversations.
export default async function UsersPage({ searchParams }: PageProps<"/users">) {
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
      <header className={styles.header}>
        <h1>Users &amp; chats</h1>
        <p className={styles.muted}>Most recently active first, {PAGE_SIZE} per page</p>
      </header>

      <section className={styles.card} aria-label="Users">
        <div className={styles.toolbar}>
          {/* Filters (a plain GET form: the filter lands in the URL (shareable, Back works), no JavaScript), then the pager */}
          <form action="/users" className={styles.filters}>
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
              <span>Company</span>
              <select name="company" defaultValue={company}>
                <option value="">All companies</option>
                {companies.ok &&
                  companies.data.map((c) => (
                    <option key={c.company_id} value={c.company_id}>
                      {c.name} ({c.company_id})
                    </option>
                  ))}
              </select>
            </label>
            <button type="submit" className={styles.apply}>
              Apply filter
            </button>
            {(app || company) && (
              <Link href="/users" className={styles.clear}>
                Clear filter
              </Link>
            )}
          </form>
          {users.ok && <Pager page={page} count={users.data.length} pageSize={PAGE_SIZE} noun="Users" href={pageHref} />}
        </div>
        {!users.ok ? (
          <Problem message={displayMessage(users.error)} />
        ) : users.data.length === 0 ? (
          <p className={styles.muted}>
            {page > 1
              ? "No more users."
              : app
                ? "No one in this app has chatted yet."
                : "No one has chatted yet. Users appear here after their first question."}
          </p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">User</th>
                  <th scope="col">App</th>
                  <th scope="col">Company</th>
                  <th scope="col" className={styles.nowrap}>
                    Role label
                  </th>
                  <th scope="col" className={styles.number}>
                    Conversations
                  </th>
                  <th scope="col" className={styles.number}>
                    Messages
                  </th>
                  <th scope="col">Last active</th>
                </tr>
              </thead>
              <tbody>
                {users.data.map((u) => (
                  <tr key={`${u.app_id}/${u.company_id}/${u.user_id}`}>
                    <td className={styles.nowrap}>
                      <Link
                        href={`/users/${encodeURIComponent(u.app_id)}/${encodeURIComponent(u.user_id)}?company=${encodeURIComponent(u.company_id)}`}
                        className="mono"
                        translate="no"
                      >
                        {u.user_id}
                      </Link>
                    </td>
                    <td className={`mono ${styles.nowrap}`} translate="no">
                      {u.app_id}
                    </td>
                    <td className={styles.nowrap}>{companyNames.get(u.company_id) ?? u.company_id}</td>
                    <td className={styles.muted}>{u.user_role ?? "–"}</td>
                    <td className={styles.number}>{formatCount(u.conversations)}</td>
                    <td className={styles.number}>{formatCount(u.messages)}</td>
                    <td className={styles.nowrap}>{u.last_active ? formatDateTime(u.last_active) : "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
