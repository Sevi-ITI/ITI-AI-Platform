import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import { formatCount, formatDateTime } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";

import Pager from "../../../pager";
import styles from "../../../dashboard.module.css";
import { Problem } from "../../../widgets";
import DeleteChats from "./delete-chats";

// The tab title names the person, so several open users can be told apart
export async function generateMetadata({ params }: { params: Promise<{ app: string; user: string }> }) {
  const { app, user } = await params;
  return { title: `${user} in ${app}` }; // already decoded here (unlike the page's params)
}

const PAGE_SIZE = 50;

// One person's conversations: one app, one company (?company=, default ITI), newest first, optionally in one
// collection (?collection=). Each opens its thread. Super admins can erase this person's chats (whatever the filter).
// Params typed by hand: route types are generated at build time (same as chat/[id]).
export default async function UserChatsPage({
  params,
  searchParams,
}: {
  params: Promise<{ app: string; user: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [{ app, user }, query] = await Promise.all([params, searchParams]);
  const appId = decodeURIComponent(app);
  const userId = decodeURIComponent(user);
  const one = (v: string | string[] | undefined) => (typeof v === "string" ? v.trim() : "");
  const collection = one(query.collection);
  const companyId = one(query.company) || "iti";
  const page = Math.max(1, Number.parseInt(one(query.page), 10) || 1);

  const [conversations, collections, companies, me] = await Promise.all([
    callApi((api) =>
      api.GET("/v1/admin/conversations", {
        params: {
          query: {
            app_id: appId,
            company_id: companyId,
            user_id: userId,
            collection: collection || undefined,
            limit: PAGE_SIZE,
            offset: (page - 1) * PAGE_SIZE,
          },
        },
      }),
    ),
    callApi((api) => api.GET("/v1/admin/collections")),
    callApi((api) => api.GET("/v1/admin/companies")),
    currentAccount(),
  ]);
  endSessionOn401(conversations, collections, companies, me);
  const companyName = (companies.ok && companies.data.find((c) => c.company_id === companyId)?.name) || companyId;

  const base = `/users/${encodeURIComponent(appId)}/${encodeURIComponent(userId)}`;
  // Same filter, another page
  const pageHref = (p: number) => {
    const q = new URLSearchParams({ company: companyId });
    if (collection) q.set("collection", collection);
    if (p > 1) q.set("page", String(p));
    const s = q.toString();
    return s ? `${base}?${s}` : base;
  };
  const isSuperAdmin = me.ok && me.data.role === "super_admin";
  // With a filter on, an empty page doesn't mean the user has no chats elsewhere
  const hasChats = conversations.ok && (conversations.data.length > 0 || page > 1 || Boolean(collection));

  return (
    <>
      <nav aria-label="Breadcrumb">
        <Link
          href={`/users?app=${encodeURIComponent(appId)}&company=${encodeURIComponent(companyId)}`}
          className={styles.muted}
        >
          ← Users of {appId} at {companyName}
        </Link>
      </nav>
      <header className={styles.header}>
        <h1>
          <span className="mono" translate="no">
            {userId}
          </span>
          <span className={styles.muted}>
            {" "}
            in{" "}
            <span className="mono" translate="no">
              {appId}
            </span>{" "}
            at {companyName}
          </span>
        </h1>
        {/* Hidden for supervisors only as a courtesy: FastAPI refuses them anyway */}
        {isSuperAdmin && hasChats && <DeleteChats appId={appId} companyId={companyId} userId={userId} />}
      </header>

      <section className={styles.card} aria-label="Conversations">
        <div className={styles.toolbar}>
          {/* Filters (a plain GET form: the filter lands in the URL (shareable, Back works), no JavaScript), then the pager */}
          <form action={base} className={styles.filters}>
            <input type="hidden" name="company" value={companyId} />
            <label>
              <span>Collection</span>
              <select name="collection" defaultValue={collection}>
                <option value="">All collections</option>
                {collections.ok &&
                  collections.data.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
              </select>
            </label>
            <button type="submit" className={styles.apply}>
              Apply filter
            </button>
            {collection && (
              <Link href={`${base}?company=${encodeURIComponent(companyId)}`} className={styles.clear}>
                Clear filter
              </Link>
            )}
          </form>
          {conversations.ok && (
            <Pager
              page={page}
              count={conversations.data.length}
              pageSize={PAGE_SIZE}
              noun="Conversations"
              href={pageHref}
            />
          )}
        </div>
        {!conversations.ok ? (
          <Problem message={displayMessage(conversations.error)} />
        ) : conversations.data.length === 0 ? (
          <p className={styles.muted}>
            {page > 1
              ? "No more conversations."
              : collection
                ? "No conversations for this user in this collection."
                : "No conversations for this user in this app (none yet, or deleted)."}
          </p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">First question</th>
                  <th scope="col">Collection</th>
                  <th scope="col" className={styles.number}>
                    Messages
                  </th>
                  <th scope="col">Started</th>
                  <th scope="col" className={styles.nowrap}>
                    Last message
                  </th>
                </tr>
              </thead>
              <tbody>
                {conversations.data.map((c) => (
                  <tr key={c.conversation_id}>
                    <td>
                      <Link
                        href={`${base}/${encodeURIComponent(c.conversation_id)}?company=${encodeURIComponent(companyId)}`}
                      >
                        {c.first_question}
                      </Link>
                    </td>
                    <td className={`mono ${styles.nowrap}`} translate="no">
                      {c.collection}
                    </td>
                    <td className={styles.number}>{formatCount(c.messages)}</td>
                    <td className={styles.nowrap}>{formatDateTime(c.created_at)}</td>
                    <td className={styles.nowrap}>{c.last_message_at ? formatDateTime(c.last_message_at) : "–"}</td>
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
