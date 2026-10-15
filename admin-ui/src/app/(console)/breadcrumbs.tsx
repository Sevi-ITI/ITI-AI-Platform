import Link from "next/link";

import styles from "./dashboard.module.css";

// The trail above a deep page (Users & chats › user › conversation). Every step but the last is a link; the last is
// the page itself (aria-current). Separators come from CSS, so screen readers read only the names.

export type Crumb = { label: React.ReactNode; href?: string };

export default function Breadcrumbs({ trail }: { trail: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb">
      <ol className={styles.crumbs}>
        {trail.map((c, i) => (
          <li key={i}>
            {c.href && i < trail.length - 1 ? (
              <Link href={c.href}>{c.label}</Link>
            ) : (
              <span aria-current="page">{c.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
