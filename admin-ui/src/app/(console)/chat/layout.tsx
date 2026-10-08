import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { endSessionOn401 } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";

import { Problem } from "../widgets";
import styles from "./chat.module.css";
import ConversationList from "./conversation-list";
import { myConversations } from "./data";

// Chat: the open conversation (or a new one) in the middle, your conversations on the right.
export default async function ChatLayout({ children }: { children: React.ReactNode }) {
  const conversations = await myConversations();
  endSessionOn401(conversations);

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
              when: formatDateTime(c.created_at),
            }))}
          />
        ) : (
          <Problem message={displayMessage(conversations.error)} />
        )}
      </aside>
    </div>
  );
}
