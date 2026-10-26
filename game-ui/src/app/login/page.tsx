import type { Metadata } from "next";

import { apiUrl } from "@/lib/api/client";

import LoginForm from "./login-form";
import styles from "./login.module.css";

export const metadata: Metadata = { title: "Log in" };

/** Is the AI service (FastAPI) answering? Its public /health check, at most 2 s so a stopped service never holds
 * up the login page. The page shows the answer only, never the internal address. (Same check as admin-ui.) */
async function aiServiceUp(): Promise<boolean> {
  try {
    const r = await fetch(`${apiUrl()}/health`, { cache: "no-store", signal: AbortSignal.timeout(2000) });
    return r.ok;
  } catch {
    return false; // not running, not reachable, too slow, or ITI_API_URL not set
  }
}

export default async function LoginPage() {
  const up = await aiServiceUp();

  return (
    <main className={styles.hero}>
      <div className={styles.copy}>
        <p className={styles.kicker}>Intellismart Technology Inc.</p>
        <h1>ITI AI HQ</h1>
        <p className={styles.lead}>The ITI AI Console as a building: walk to a room to open its page.</p>
        <div className={styles.places}>
          <p className={`${styles.place} ${up ? "" : styles.placeDown}`} title="Checked when this page opened">
            <span className={up ? styles.placeDot : styles.placeCross} aria-hidden="true" />
            {up ? "AI service connected" : "AI service not reachable"}
          </p>
        </div>
      </div>
      <LoginForm />
    </main>
  );
}
