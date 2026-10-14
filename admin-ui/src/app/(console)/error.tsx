"use client";

import Link from "next/link";

import styles from "./dashboard.module.css";

// A page broke while rendering (FastAPI errors are shown inside the pages; this catches the rest). The sidebar stays,
// so the person can retry or go elsewhere. Next 16: retry() re-fetches the page; the digest matches the server log.
export default function PageError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <section className={`${styles.card} ${styles.pageError}`} role="alert">
      <h1 className={styles.panelTitle}>This page couldn&apos;t load</h1>
      <p className={styles.muted}>
        Something went wrong while showing it. Try again; if it keeps happening, check that FastAPI is running.
      </p>
      {error.digest && (
        <p className={styles.muted}>
          Reference: <span className="mono">{error.digest}</span>
        </p>
      )}
      <div className={styles.rowActions}>
        <button type="button" className={styles.apply} onClick={() => retry()}>
          Try again
        </button>
        <Link href="/" className={styles.clear}>
          Go to Overview
        </Link>
      </div>
    </section>
  );
}
