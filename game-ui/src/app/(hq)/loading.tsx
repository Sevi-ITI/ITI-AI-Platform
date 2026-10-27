// Copied from admin-ui src/app/(console)/loading.tsx (G7): shown in the room panel while the page waits for FastAPI.
import styles from "./kit/dashboard.module.css";

// Shown at once while a console page waits for FastAPI (Next wraps every page below in Suspense with this).
// Shaped like a page: title, a toolbar, rows, so nothing jumps when the real page arrives.
export default function Loading() {
  return (
    <div className={styles.skeleton} aria-busy="true">
      <p role="status" className="sr-only">
        Loading…
      </p>
      <div className={styles.skeletonTitle} />
      <div className={styles.card} aria-hidden="true">
        <div className={styles.skeletonBar} />
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div key={i} className={styles.skeletonLine} />
        ))}
      </div>
    </div>
  );
}
