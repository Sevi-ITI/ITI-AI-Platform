import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { displayMessage } from "@/lib/api/api-error";
import { logOut } from "@/lib/session/actions";
import { currentAccount } from "@/lib/session/current-account";
import { THEME_COOKIE, themeFrom } from "@/lib/theme";
import { toggleTheme } from "@/lib/theme-actions";

import styles from "./console.module.css";
import NavLinks from "./nav-links";

export default async function ConsoleLayout({ children }: { children: React.ReactNode }) {
  const me = await currentAccount();
  if (!me.ok) {
    if (me.error.status === 401) {
      redirect("/session-ended");
    }
    return (
      <main className={styles.problem}>
        <div className={styles.card}>
          <h1>The console can&apos;t load</h1>
          <p role="alert">{displayMessage(me.error)}</p>
          <Link href="/">Try again</Link>
          <form action={logOut}>
            <button type="submit" className={styles.quiet}>
              Log out
            </button>
          </form>
        </div>
      </main>
    );
  }

  const account = me.data;
  const theme = themeFrom((await cookies()).get(THEME_COOKIE)?.value);

  return (
    <div className={styles.shell}>
      <a href="#content" className={styles.skip}>
        Skip to content
      </a>
      <aside className={styles.sidebar}>
        <p className={styles.brand}>ITI AI Console</p>
        <nav aria-label="Console">
          <NavLinks showAccounts={account.role === "super_admin"} />
        </nav>
        <div className={styles.account}>
          <p className={styles.name}>{account.display_name ?? account.username}</p>
          <span className={styles.role} translate="no">
            {account.role}
          </span>
          <form action={toggleTheme}>
            <button type="submit" className={styles.quiet}>
              {theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            </button>
          </form>
          <form action={logOut}>
            <button type="submit" className={styles.quiet}>
              Log out
            </button>
          </form>
        </div>
      </aside>
      <main id="content" className={styles.content}>
        {children}
      </main>
    </div>
  );
}
