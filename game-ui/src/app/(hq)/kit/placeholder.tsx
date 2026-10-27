import styles from "./dashboard.module.css";

// Copied from admin-ui src/app/(console)/placeholder.tsx (G6): what Accounts and Tools & MCP show anyone but a super
// admin. In game-ui the shell already locks those rooms, so this is only a fallback. Its title is an <h2> (the panel
// has the <h1>) and it uses the kit's styles.
export default function Placeholder({ title, step, children }: { title: string; step: string; children: React.ReactNode }) {
  return (
    <section className={styles.card}>
      <p className={styles.muted}>{step}</p>
      <h2>{title}</h2>
      <p className={styles.muted}>{children}</p>
    </section>
  );
}
