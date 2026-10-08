import type { Metadata } from "next";

import LoginForm from "./login-form";
import styles from "./login.module.css";

export const metadata: Metadata = { title: "Log in" };

export default function LoginPage() {
  return (
    <main className={styles.hero}>
      <div className={styles.copy}>
        <p className={styles.kicker}>Intellismart Technology Inc.</p>
        <h1>ITI AI Console</h1>
        <p className={styles.lead}>
          Monitor and control the ITI AI Platform: requests, chats, documents, keys and accounts.
        </p>
      </div>
      <LoginForm />
    </main>
  );
}
