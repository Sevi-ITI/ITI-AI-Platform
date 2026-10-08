import styles from "./console.module.css";

// Stand-in for a page that a later step fills (6B.2-6B.5).
export default function Placeholder({ title, step, children }: { title: string; step: string; children: React.ReactNode }) {
  return (
    <section className={styles.card}>
      <p className={styles.kicker}>{step}</p>
      <h1>{title}</h1>
      <p className={styles.muted}>{children}</p>
    </section>
  );
}
