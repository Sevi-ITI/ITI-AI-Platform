import type { Metadata } from "next";
import { headers } from "next/headers";

import { apiUrl } from "@/lib/api/client";

import { DocumentsIcon, KeysIcon, OverviewIcon } from "../(console)/icons";
import LoginForm from "./login-form";
import styles from "./login.module.css";

export const metadata: Metadata = { title: "Log in" };

/** Which console this is, from the address it was opened at (never a fixed address): "Local · 127.0.0.1:3000" on
 * this laptop, the office server's name or address on another machine. Behind a reverse proxy (Phase 9) the
 * address the person typed comes in X-Forwarded-Host, so that one wins. Nothing to configure. */
function placeOf(forwarded: string | null, host: string | null): string {
  const address = forwarded?.split(",")[0].trim() || host;
  if (!address) return "Unknown server";
  const local = /^(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$/.test(address);
  return local ? `Local · ${address}` : address;
}

/** Is the AI service (FastAPI) answering? Its public /health check (no login, no database or model call), at the
 * address in ITI_API_URL (admin-ui\.env.local: set per machine, not in the code). At most 2 s, so a stopped
 * service never holds up the login page. The page shows the answer only, never the internal address. */
async function aiServiceUp(): Promise<boolean> {
  try {
    const r = await fetch(`${apiUrl()}/health`, { cache: "no-store", signal: AbortSignal.timeout(2000) });
    return r.ok;
  } catch {
    return false; // not running, not reachable, too slow, or ITI_API_URL not set
  }
}

export default async function LoginPage() {
  const request = await headers();
  const place = placeOf(request.get("x-forwarded-host"), request.get("host"));
  const up = await aiServiceUp();

  return (
    <main className={styles.hero}>
      <div className={styles.copy}>
        <p className={styles.kicker}>Intellismart Technology Inc.</p>
        <h1>ITI AI Console</h1>
        <p className={styles.lead}>
          Monitor and control the ITI AI Platform: requests, chats, documents, keys and accounts.
        </p>
        {/* what is inside, in three lines (the icons are decoration) */}
        <ul className={styles.features}>
          <li>
            <OverviewIcon />
            System health, answer times and every request
          </li>
          <li>
            <DocumentsIcon />
            The documents and collections the AI answers from
          </li>
          <li>
            <KeysIcon />
            Apps, keys, companies and console accounts
          </li>
        </ul>
        {/* where this console runs, and whether the AI service behind it answers (shape + words, not color alone) */}
        <div className={styles.places}>
          <p className={styles.place} title="The server this console is running on">
            <span className={styles.placeDot} aria-hidden="true" />
            {place}
          </p>
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
