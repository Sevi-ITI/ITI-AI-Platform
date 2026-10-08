import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import { formatDateTime, formatStamp } from "@/lib/format";

import Message from "../../../../chat/message";
import styles from "../../../../dashboard.module.css";
import { Problem } from "../../../../widgets";

export async function generateMetadata({ params }: { params: Promise<{ app: string; user: string }> }) {
  const { user } = await params;
  return { title: `Conversation of ${user}` }; // already decoded here (unlike the page's params)
}

// What rag decided for each answer (AdminMessage.reason), in words. Unknown values show as they are.
const OUTCOMES: Record<string, { label: string; ok: boolean }> = {
  answered: { label: "Answered", ok: true },
  no_relevant_chunks: { label: "“I don’t know”: no matching passages", ok: false },
  model_refused: { label: "“I don’t know”: the model found no answer", ok: false },
  check_failed: { label: "“I don’t know”: the answer failed the check", ok: false },
  blank: { label: "“I don’t know”: empty answer", ok: false },
};

// One conversation as the user saw it (questions, answers, sources), plus each answer's outcome, time and
// request id for review. Read-only. Params typed by hand: route types are generated at build time.
export default async function ThreadPage({
  params,
}: {
  params: Promise<{ app: string; user: string; conversation: string }>;
}) {
  const { app, user, conversation } = await params;
  const appId = decodeURIComponent(app);
  const userId = decodeURIComponent(user);
  const conversationId = decodeURIComponent(conversation);

  const [messages, summaries] = await Promise.all([
    callApi((api) =>
      api.GET("/v1/admin/conversations/{conversation_id}/messages", {
        params: { path: { conversation_id: conversationId } },
      }),
    ),
    // ponytail: the collection and start time come from this user's 200 newest conversations; an older
    // one still shows its messages, just without that line.
    callApi((api) =>
      api.GET("/v1/admin/conversations", { params: { query: { app_id: appId, user_id: userId, limit: 200 } } }),
    ),
  ]);
  endSessionOn401(messages, summaries);

  const summary = summaries.ok ? summaries.data.find((c) => c.conversation_id === conversationId) : undefined;
  const userPage = `/users/${encodeURIComponent(appId)}/${encodeURIComponent(userId)}`;
  const requestLog = `/requests?app=${encodeURIComponent(appId)}&user=${encodeURIComponent(userId)}`;

  return (
    <>
      <nav aria-label="Breadcrumb">
        <Link href={userPage} className={styles.muted}>
          ← Conversations of {userId} in {appId}
        </Link>
      </nav>
      <header className={styles.header}>
        <h1>Conversation</h1>
        {summary && (
          <p className={styles.muted}>
            Collection{" "}
            <span className="mono" translate="no">
              {summary.collection}
            </span>
            , started {formatDateTime(summary.created_at)}
          </p>
        )}
      </header>

      {!messages.ok ? (
        <section className={styles.card}>
          <Problem message={displayMessage(messages.error)} />
          <Link href={userPage}>Back to this user&apos;s conversations</Link>
        </section>
      ) : messages.data.length === 0 ? (
        <p className={styles.muted}>This conversation has no messages.</p>
      ) : (
        <section className={styles.thread} aria-label="Messages">
          {messages.data.map((m, i) => {
            const outcome = m.reason ? (OUTCOMES[m.reason] ?? { label: m.reason, ok: false }) : null;
            return (
              <div key={`${m.request_id}-${m.role}-${i}`} className={styles.turn}>
                <Message role={m.role === "user" ? "user" : "assistant"} content={m.content} citations={m.citations} />
                <p className={m.role === "user" ? `${styles.turnMeta} ${styles.turnMetaUser}` : styles.turnMeta}>
                  {outcome && (
                    <span className={outcome.ok ? styles.ok : undefined}>
                      {outcome.ok ? "●" : "○"} {outcome.label} ·{" "}
                    </span>
                  )}
                  {formatStamp(m.created_at)}
                  {m.role !== "user" && (
                    <>
                      {" · "}
                      <Link href={`${requestLog}#${m.request_id}`} className="mono" translate="no">
                        {m.request_id}
                      </Link>
                    </>
                  )}
                </p>
              </div>
            );
          })}
        </section>
      )}
    </>
  );
}
