"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./chat.module.css";

export type ConversationItem = { id: string; title: string; collection: string; when: string };

// Client only for the highlight: it needs the current URL.
export default function ConversationList({ items }: { items: ConversationItem[] }) {
  const pathname = usePathname();

  if (items.length === 0) {
    return <p className={styles.muted}>No conversations yet. Your questions appear here.</p>;
  }
  return (
    <ul className={styles.list}>
      {items.map((c) => (
        <li key={c.id}>
          <Link href={`/chat/${c.id}`} aria-current={pathname === `/chat/${c.id}` ? "page" : undefined}>
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
  );
}
