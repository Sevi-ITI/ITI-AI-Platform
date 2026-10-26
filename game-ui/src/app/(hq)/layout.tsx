import Link from "next/link";
import { redirect } from "next/navigation";

import { displayMessage } from "@/lib/api/api-error";
import { logOut } from "@/lib/session/actions";
import { currentAccount } from "@/lib/session/current-account";

import styles from "./hq.module.css";

// Every HQ page sits inside this: who is logged in (GET /v1/console/me) and a way out. A 401 means the session
// is over → /session-ended clears the cookie. The 3D building replaces this plain frame in G2.
export default async function HqLayout({ children }: { children: React.ReactNode }) {
  const me = await currentAccount();
  if (!me.ok) {
    if (me.error.status === 401) {
      redirect("/session-ended");
    }
    return (
      <main className={styles.problem}>
        <div className={styles.card}>
          <h1>The HQ can&apos;t load</h1>
          <p role="alert">{displayMessage(me.error)}</p>
          <Link href="/">Try again</Link>
          <form action={logOut}>
            <button type="submit" className={styles.button}>
              Log out
            </button>
          </form>
        </div>
      </main>
    );
  }

  const account = me.data;

  return (
    <div className={styles.shell}>
      <header className={styles.bar}>
        <p className={styles.brand}>ITI AI HQ</p>
        <div className={styles.who}>
          <span>{account.display_name ?? account.username}</span>
          <span className={styles.role} translate="no">
            {account.role}
          </span>
          <form action={logOut}>
            <button type="submit" className={styles.button}>
              Log out
            </button>
          </form>
        </div>
      </header>
      <main id="content" className={styles.content}>
        {children}
      </main>
    </div>
  );
}
