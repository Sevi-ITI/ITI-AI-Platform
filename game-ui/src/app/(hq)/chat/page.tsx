import type { Metadata } from "next";

import styles from "../hq.module.css";

export const metadata: Metadata = { title: "Chat" };

// Testers land here after login (the shared logIn action sends them to /chat). The real Chat room comes later.
export default function ChatRoom() {
  return (
    <section className={styles.card}>
      <h1>Chat</h1>
      <p>The Chat room is not built yet.</p>
    </section>
  );
}
