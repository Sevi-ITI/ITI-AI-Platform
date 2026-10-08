import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import { formatCount, formatDateTime } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";

import styles from "../../../dashboard.module.css";
import { Problem } from "../../../widgets";
import DeleteChats from "./delete-chats";

// The tab title names the person, so several open users can be told apart
export async function generateMetadata({ params }: { params: Promise<{ app: string; user: string }> }) {
  const { app, user } = await params;
  return { title: `${user} in ${app}` }; // already decoded here (unlike the page's params)
}

const PAGE_SIZE = 50;

// One user's conversations in one app, newest first, optionally in one collection (?collection=, in the URL);
// each opens its thread. Super admins can erase all of this user's chats in this app (whatever the filter).
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
  const page = Math.max(1, Number.parseInt(one(query.page), 10) || 1);

  const [conversations, collections, me] = await Promise.all([
    callApi((api) =>
      api.GET("/v1/admin/conversations", {
        params: {
          query: {
            app_id: appId,
            user_id: userId,
            collection: collection || undefined,
            limit: PAGE_SIZE,
            offset: (page - 1) * PAGE_SIZE,
          },
        },
      }),
    ),
    callApi((api) => api.GET("/v1/admin/collections")),
    currentAccount(),
  ]);
  endSessionOn401(conversations, collections, me);

  const base = `/users/${encodeURIComponent(appId)}/${encodeURIComponent(userId)}`;
  // Same filter, another page
  const pageHref = (p: number) => {
    const q = new URLSearchParams();
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
        <Link href={`/users?app=${encodeURIComponent(appId)}`} className={styles.muted}>
          ← Users of {appId}
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
            </span>
          </span>
        </h1>
        {/* Hidden for supervisors only as a courtesy: FastAPI refuses them anyway */}
        {isSuperAdmin && hasChats && <DeleteChats appId={appId} userId={userId} />}
      </header>

      {/* A plain GET form: the filter lands in the URL (shareable, Back works), no JavaScript */}
      <form action={base} className={styles.filters}>
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
          <Link href={base} className={styles.clear}>
            Clear filter
          </Link>
        )}
      </form>

      <section className={styles.card} aria-label="Conversations">
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
                      <Link href={`${base}/${encodeURIComponent(c.conversation_id)}`}>{c.first_question}</Link>
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

      {conversations.ok && (page > 1 || conversations.data.length === PAGE_SIZE) && (
        <nav aria-label="Pages" className={styles.pager}>
          {page > 1 ? <Link href={pageHref(page - 1)}>← Previous</Link> : <span />}
          {conversations.data.length > 0 ? (
            <span className={styles.muted}>
              Conversations {formatCount((page - 1) * PAGE_SIZE + 1)}–
              {formatCount((page - 1) * PAGE_SIZE + conversations.data.length)}
            </span>
          ) : (
            <span />
          )}
          {/* ponytail: the API gives no total, so "Next" shows whenever this page is full */}
          {conversations.data.length === PAGE_SIZE ? <Link href={pageHref(page + 1)}>Next →</Link> : <span />}
        </nav>
      )}
    </>
  );
}
