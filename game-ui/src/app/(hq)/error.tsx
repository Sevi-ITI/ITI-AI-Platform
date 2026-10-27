"use client";
// Copied from admin-ui src/app/(console)/error.tsx (G7). In the HQ the shell stays around it (3D or list); its title is an
// <h2> (the panel has the <h1>).

import Link from "next/link";

import styles from "./kit/dashboard.module.css";

// A page broke while rendering (FastAPI errors are shown inside the pages; this catches the rest). The sidebar stays,
// so the person can retry or go elsewhere. Next 16: retry() re-fetches the page; the digest matches the server log.
export default function PageError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <section className={`${styles.card} ${styles.pageError}`} role="alert">
      <h2 className={styles.panelTitle}>This page couldn&apos;t load</h2>
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
