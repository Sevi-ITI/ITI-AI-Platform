import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { displayMessage } from "@/lib/api/api-error";
import { logOut } from "@/lib/session/actions";
import { currentAccount } from "@/lib/session/current-account";
import { VIEW_COOKIE, viewFrom } from "@/hq/view";

import HqShell from "./hq-shell";
import styles from "./hq.module.css";

// Every HQ page sits inside this: who is logged in (GET /v1/console/me) decides which rooms open; the view cookie
// decides 3D or list. A 401 means the session is over → /session-ended clears the cookie.
export default async function HqLayout({ children }: { children: React.ReactNode }) {
  const me = await currentAccount();
  if (!me.ok) {
    if (me.error.status === 401) {
      redirect("/session-ended");
    }
    return (
      <main className={styles.problem}>
        <div className={styles.problemCard}>
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
  const view = viewFrom((await cookies()).get(VIEW_COOKIE)?.value);

  return (
    <HqShell name={account.display_name ?? account.username} role={account.role} view={view}>
      {children}
    </HqShell>
  );
}
