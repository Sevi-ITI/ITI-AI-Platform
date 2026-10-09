import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { displayMessage } from "@/lib/api/api-error";
import { logOut } from "@/lib/session/actions";
import { currentAccount } from "@/lib/session/current-account";
import { THEME_COOKIE, themeFrom } from "@/lib/theme";
import { toggleTheme } from "@/lib/theme-actions";

import styles from "./console.module.css";
import { LogOutIcon, MoonIcon, SunIcon } from "./icons";
import NavLinks from "./nav-links";
import Toaster from "./toast";

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
        <p className={styles.brand}>
          <span className={styles.brandShort} aria-hidden="true">
            ITI
          </span>
          <span className={styles.label}>ITI AI Console</span>
        </p>
        <nav aria-label="Console">
          <NavLinks showAccounts={account.role === "super_admin"} />
        </nav>
        <div className={styles.account}>
          <div className={styles.who}>
            <p className={styles.name}>{account.display_name ?? account.username}</p>
            <span className={styles.role} translate="no">
              {account.role}
            </span>
          </div>
          <form action={toggleTheme}>
            {/* title = hover hint for mouse users; aria-label = the name screen readers announce */}
            <button
              type="submit"
              className={styles.iconButton}
              aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
              title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            >
              {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            </button>
          </form>
          <form action={logOut}>
            <button type="submit" className={styles.iconButton} aria-label="Log out" title="Log out">
              <LogOutIcon />
            </button>
          </form>
        </div>
      </aside>
      <main id="content" className={styles.content}>
        {children}
      </main>
      <Toaster />
    </div>
  );
}
