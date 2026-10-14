"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./chat.module.css";

export type ConversationItem = { id: string; title: string; collection: string; group: string; when: string };

// Client only for the highlight: it needs the current URL. Items arrive newest first, already grouped by day
// (Today / Yesterday / Earlier); each group gets a small heading.
export default function ConversationList({ items }: { items: ConversationItem[] }) {
  const pathname = usePathname();

  if (items.length === 0) {
    return <p className={styles.muted}>No conversations yet. Your questions appear here.</p>;
  }
  const groups = [...new Set(items.map((c) => c.group))];
  return (
    <div className={styles.groups}>
      {groups.map((g) => (
        <section key={g} aria-label={g}>
          <h3 className={styles.listGroup}>{g}</h3>
          <ul className={styles.list}>
            {items
              .filter((c) => c.group === g)
              .map((c) => (
                <li key={c.id}>
                  {/* scroll={false}: the conversation scrolls itself to its latest message (composer.tsx);
                      title: the whole question on hover (the line is cut to fit) */}
                  <Link
                    href={`/chat/${c.id}`}
                    scroll={false}
                    title={c.title}
                    aria-current={pathname === `/chat/${c.id}` ? "page" : undefined}
                  >
                    <span className={styles.listTitle}>{c.title}</span>
                    <span className={styles.listMeta}>
                      <span className="mono" translate="no">
                        {c.collection}
                      </span>
                      , {c.when}
                    </span>
                  </Link>
                </li>
              ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
