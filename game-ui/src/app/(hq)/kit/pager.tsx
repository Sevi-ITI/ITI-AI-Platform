import Link from "next/link";

import { formatCount } from "@/lib/format";

import styles from "./dashboard.module.css";

// Previous / Next above a paged table, at its top right (Request log, Users, a user's conversations, Documents).
// ponytail: the API gives no total, so "Next" shows whenever this page is full.
export default function Pager({
  page,
  count,
  pageSize,
  noun,
  href,
}: {
  page: number;
  count: number; // rows on this page
  pageSize: number;
  noun: string; // "Rows", "Users", ...
  href: (page: number) => string;
}) {
  if (page === 1 && count < pageSize) return null;
  const first = (page - 1) * pageSize + 1;

  return (
    <nav aria-label="Pages" className={styles.pager}>
      {count > 0 && (
        <span className={styles.muted}>
          {noun} {formatCount(first)}–{formatCount(first + count - 1)}
        </span>
      )}
      {page > 1 && <Link href={href(page - 1)}>← Previous</Link>}
      {count === pageSize && <Link href={href(page + 1)}>Next →</Link>}
    </nav>
  );
}
