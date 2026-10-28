// One user's conversations, decluttered for game-ui like Apps & keys (Vince, 2026-10-28). Not a copy of admin-ui's
// page any more: the same FastAPI calls (check:parity) and the same delete dialog (delete-chats.tsx: a copy,
// check:rooms), a calmer layout: who they are with the collection filter at the top right, one line per conversation
// instead of a five-column table, and erasing their chats as a quiet strip at the bottom (was a big red card).
import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import { formatCount, formatDateTime, initials } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import Breadcrumbs from "../../../kit/breadcrumbs";
import Pager from "../../../kit/pager";
import styles from "../../../kit/dashboard.module.css";
import { Problem } from "../../../kit/widgets";
import css from "../../users.module.css";
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
  await testersGoToChat(); // testers have only the Chat page
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
    return `${base}?${q.toString()}`;
  };
  const isSuperAdmin = me.ok && me.data.role === "super_admin";
  // With a filter on, an empty page doesn't mean the user has no chats elsewhere
  const hasChats = conversations.ok && (conversations.data.length > 0 || page > 1 || Boolean(collection));

  return (
    <>
      <Breadcrumbs
        trail={[
          { label: "Users & chats", href: "/users" },
          {
            label: `${appId} at ${companyName}`,
            href: `/users?app=${encodeURIComponent(appId)}&company=${encodeURIComponent(companyId)}`,
          },
          { label: userId },
        ]}
      />

      {/* who on the left, the collection filter at the top right */}
      <div className={css.userHead}>
        <span className={styles.appAvatar} aria-hidden="true">
          {initials(userId)}
        </span>
        <div className={css.who}>
          <h2 className={`mono ${css.userTitle}`} translate="no">
            {userId}
          </h2>
          <span className={styles.kpiNote}>
            chats in{" "}
            <span className="mono" translate="no">
              {appId}
            </span>{" "}
            | {companyName}
          </span>
        </div>
        <form action={base} className={css.filters}>
          <input type="hidden" name="company" value={companyId} />
          <label>
            <span className="sr-only">Collection</span>
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
          <button type="submit" className={styles.filterApply}>
            Filter
          </button>
          {collection && (
            <Link href={`${base}?company=${encodeURIComponent(companyId)}`} className={styles.clear}>
              Clear
            </Link>
          )}
        </form>
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
        <section className={`${styles.card} ${css.list}`} aria-label="Conversations">
          <p className={css.listTitle}>
            {formatCount(conversations.data.length)}
            {conversations.data.length === PAGE_SIZE ? "+" : ""} conversations | newest first
          </p>
          <ul className={css.rows}>
            {conversations.data.map((c) => (
              <li key={c.conversation_id} className={css.chatRow}>
                <Link
                  href={`${base}/${encodeURIComponent(c.conversation_id)}?company=${encodeURIComponent(companyId)}`}
                  className={css.question}
                >
                  {c.first_question}
                </Link>
                <span className={`mono ${css.where}`} translate="no">
                  {c.collection}
                </span>
                <span className={css.counts}>
                  <b>{formatCount(c.messages)}</b> {c.messages === 1 ? "message" : "messages"}
                </span>
                <span className={css.when}>
                  {formatDateTime(c.last_message_at ?? c.created_at)}
                  {c.last_message_at && c.last_message_at !== c.created_at && (
                    <span className={styles.kpiNote}> | started {formatDateTime(c.created_at)}</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
          {(page > 1 || conversations.data.length === PAGE_SIZE) && (
            <Pager page={page} count={conversations.data.length} pageSize={PAGE_SIZE} noun="Conversations" href={pageHref} />
          )}
        </section>
      )}

      {/* Hidden for supervisors only as a courtesy: FastAPI refuses them anyway */}
      {isSuperAdmin && hasChats && (
        <div className={css.danger}>
          <span className={styles.kpiNote}>
            Erase every conversation of this user in this app, for good (request-log rows, no chat text, stay until the
            90-day clean-up)
          </span>
          <DeleteChats appId={appId} companyId={companyId} userId={userId} />
        </div>
      )}
    </>
  );
}
