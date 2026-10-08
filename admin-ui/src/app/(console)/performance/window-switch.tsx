"use client";

import Link, { useLinkStatus } from "next/link";

import styles from "../dashboard.module.css";

// The 1 h / 24 h / 7 d switch. Each window is a fresh server render (no preloading), so the clicked
// option shows a small pulsing dot until the new numbers arrive: the click is confirmed at once.

function Pending() {
  const { pending } = useLinkStatus();
  return <span aria-hidden="true" className={`${styles.pendingDot} ${pending ? styles.isPending : ""}`} />;
}

export default function WindowSwitch({
  current,
  options,
}: {
  current: string;
  options: { key: string; label: string }[];
}) {
  return (
    <nav aria-label="Time window" className={styles.switch}>
      {options.map((o) => (
        <Link
          key={o.key}
          href={`/performance?window=${o.key}`}
          prefetch={false}
          aria-current={o.key === current ? "page" : undefined}
        >
          {o.label}
          <Pending />
        </Link>
      ))}
    </nav>
  );
}
