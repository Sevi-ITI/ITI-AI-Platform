import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { endSessionOn401 } from "@/lib/api/client";
import { dayKey, formatDateTime, formatTime } from "@/lib/format";

import { Problem } from "../widgets";
import styles from "./chat.module.css";
import ConversationList from "./conversation-list";
import { myConversations } from "./data";

// Chat: the open conversation (or a new one) in the middle, your conversations on the right.
export default async function ChatLayout({ children }: { children: React.ReactNode }) {
  const conversations = await myConversations();
  endSessionOn401(conversations);
  // Grouped by Manila day, worked out here on the server (no clock mismatch in the browser)
  const now = new Date().getTime(); // a server component: rendered once per request
  const today = dayKey(new Date(now));
  const yesterday = dayKey(new Date(now - 24 * 60 * 60 * 1000));
  const group = (at: string) => (dayKey(at) === today ? "Today" : dayKey(at) === yesterday ? "Yesterday" : "Earlier");

  return (
    <div className={styles.chat}>
      <div className={styles.main}>{children}</div>
      <aside className={styles.side} aria-label="Your conversations">
        <Link href="/chat" className={styles.newChat}>
          + New chat
        </Link>
        {conversations.ok ? (
          <ConversationList
            items={conversations.data.map((c) => ({
              id: c.conversation_id,
              title: c.first_question,
              collection: c.collection,
              group: group(c.created_at),
              // Earlier: "Oct 8, 14:05"; Today / Yesterday: just "16:58"
              when:
                group(c.created_at) === "Earlier"
                  ? formatDateTime(c.created_at)
                  : formatTime(c.created_at).slice(0, 5),
            }))}
          />
        ) : (
          <Problem message={displayMessage(conversations.error)} />
        )}
      </aside>
    </div>
  );
}
