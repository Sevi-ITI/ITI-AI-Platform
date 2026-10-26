import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import styles from "./hq.module.css";

// The HQ lobby. Empty in G1: the building and its rooms come in G2.
export default async function HqHome() {
  await testersGoToChat();

  return (
    <section className={styles.card}>
      <h1>Lobby</h1>
      <p>You are logged in to the HQ. The building and its rooms are built in the next steps.</p>
    </section>
  );
}
