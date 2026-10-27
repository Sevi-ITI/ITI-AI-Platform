import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { displayMessage } from "@/lib/api/api-error";
import { logOut } from "@/lib/session/actions";
import { currentAccount } from "@/lib/session/current-account";
import { autoFrom, PHT_AUTO_COOKIE, PHT_SIM_COOKIE, simFrom } from "@/hq/pht";
import { shownTheme } from "@/hq/theme";
import { VIEW_COOKIE, viewFrom } from "@/hq/view";

import HqShell from "./hq-shell";
import styles from "./hq.module.css";
import { loadCity } from "./load-city";

// Every HQ page sits inside this: who is logged in (GET /v1/console/me) decides which rooms open; the view cookie
// decides 3D or list, the theme cookie dark or light. A 401 means the session is over → /session-ended clears the cookie.
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
  const store = await cookies();
  // The 3D HQ is for super admins (Vince, 2026-10-27); supervisors and testers always get the list view.
  const view = account.role === "super_admin" ? viewFrom(store.get(VIEW_COOKIE)?.value) : "list";
  const theme = shownTheme(store);
  const phtAuto = autoFrom(store.get(PHT_AUTO_COOKIE)?.value);
  const phtSim = simFrom(store.get(PHT_SIM_COOKIE)?.value);
  const city = view === "3d" ? await loadCity() : []; // the app city blocks: only the 3D HQ shows them

  return (
    <HqShell
      name={account.display_name ?? account.username}
      role={account.role}
      view={view}
      theme={theme}
      phtAuto={phtAuto}
      phtSim={phtSim}
      city={city}
    >
      {children}
    </HqShell>
  );
}
