import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";

import { Problem } from "../../widgets";
import styles from "../chat.module.css";
import Composer from "../composer";
import { chatCollections, myConversations } from "../data";
import Message from "../message";

export const metadata = { title: "Chat" };

export default async function ConversationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [messages, conversations, collections] = await Promise.all([
    callApi((api) => api.GET("/v1/conversations/{conversation_id}/messages", { params: { path: { conversation_id: id } } })),
    myConversations(),
    chatCollections(),
  ]);
  endSessionOn401(messages, conversations, collections);

  const summary = conversations.ok ? conversations.data.find((c) => c.conversation_id === id) : undefined;

  if (!messages.ok) {
    return (
      <section className={styles.thread}>
        <Problem message={displayMessage(messages.error)} />
        <Link href="/chat">Start a new chat</Link>
      </section>
    );
  }

  return (
    <section className={styles.thread} aria-label="Conversation">
      {summary && (
        <p className={styles.threadMeta}>
          Collection{" "}
          <span className="mono" translate="no">
            {summary.collection}
          </span>
          , started {formatDateTime(summary.created_at)}
        </p>
      )}
      {messages.data.map((m, i) => (
        <Message key={`${m.request_id}-${m.role}-${i}`} role={m.role} content={m.content} citations={m.citations} />
      ))}
      {summary ? (
        <Composer
          conversationId={id}
          fixedCollection={summary.collection}
          collections={collections.ok ? collections.data : []}
          historyCount={messages.data.length}
        />
      ) : (
        // ponytail: the collection comes from your 50 newest conversations; an older one is read-only here
        <p className={styles.muted}>
          This conversation is older than your 50 newest, so it can&apos;t be continued here.{" "}
          <Link href="/chat">Start a new chat</Link>
        </p>
      )}
    </section>
  );
}
