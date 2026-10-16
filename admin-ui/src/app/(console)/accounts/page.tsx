import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatDateTime, initials } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import ConfirmAction from "../confirm-action";
import styles from "../dashboard.module.css";
import { StatusErrorIcon, StatusOkIcon } from "../icons";
import Placeholder from "../placeholder";
import { Problem } from "../widgets";
import { updateAccount } from "./actions";
import { AddAccountButton, EditAccountButton, ResetPasswordButton } from "./dialogs";

export const metadata = { title: "Accounts" };

type Account = components["schemas"]["AccountInfo"];

// Console accounts (super admin only): who can log in, with which role. FastAPI refuses everyone else,
// and refuses a change that would leave no active super admin (409 last_super_admin).
export default async function AccountsPage() {
  await testersGoToChat(); // testers have only the Chat page
  const me = await currentAccount();
  endSessionOn401(me);
  if (!me.ok || me.data.role !== "super_admin") {
    return (
      <Placeholder title="Accounts" step="Super admin only">
        Only a super admin can see and manage console accounts. (FastAPI refuses these requests for anyone else.)
      </Placeholder>
    );
  }

  const [accounts, collections] = await Promise.all([
    callApi((api) => api.GET("/v1/admin/accounts")),
    callApi((api) => api.GET("/v1/admin/collections")),
  ]);
  endSessionOn401(accounts, collections);
  const collectionNames = collections.ok ? collections.data.map((c) => c.name).sort() : [];

  // Order: you first, then active accounts (super admins, supervisors, testers), deactivated last; A to Z inside each.
  const rank = (a: Account) =>
    a.username === me.data.username ? 0 : !a.active ? 4 : a.role === "super_admin" ? 1 : a.role === "supervisor" ? 2 : 3;
  const rows = accounts.ok
    ? [...accounts.data].sort(
        (a, b) =>
          rank(a) - rank(b) ||
          (a.display_name ?? a.username).localeCompare(b.display_name ?? b.username, "en", { sensitivity: "base" }),
      )
    : [];
  const active = rows.filter((a) => a.active);
  const admins = active.filter((a) => a.role === "super_admin").length;

  return (
    <>
      <header className={styles.header}>
        <div>
          <h1>Accounts</h1>
          {accounts.ok && (
            <p className={styles.muted}>
              {rows.length} {rows.length === 1 ? "account" : "accounts"} · {active.length} active · {admins} super{" "}
              {admins === 1 ? "admin" : "admins"}
            </p>
          )}
        </div>
        <AddAccountButton collections={collectionNames} />
      </header>

      <section className={styles.card} aria-label="Console accounts">
        {!accounts.ok ? (
          <Problem message={displayMessage(accounts.error)} />
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Person</th>
                  <th scope="col">Role</th>
                  <th scope="col">State</th>
                  <th scope="col" className={styles.nowrap}>
                    Last login
                  </th>
                  <th scope="col" className={styles.actionsCell}>
                    {/* actions */}
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((a) => (
                  <AccountRow key={a.username} a={a} isMe={a.username === me.data.username} collections={collectionNames} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}

function AccountRow({ a, isMe, collections }: { a: Account; isMe: boolean; collections: string[] }) {
  const name = a.display_name ?? a.username;
  return (
    <tr className={a.active ? undefined : styles.dimmed}>
      {/* who: tile, name (+ "you"), username under it (was two columns) */}
      <td>
        <div className={styles.person}>
          <span className={styles.avatarSm} aria-hidden="true">
            {initials(name)}
          </span>
          <div>
            <span className={styles.personName}>{name}</span>
            {isMe && <span className={styles.tag}>you</span>}
            <div className={`${styles.kpiNote} mono`} translate="no">
              {a.username}
            </div>
          </div>
        </div>
      </td>
      <td className={styles.nowrap}>
        <span className={a.role === "super_admin" ? styles.roleAdmin : styles.tag}>
          {a.role === "super_admin" ? "Super admin" : a.role === "supervisor" ? "Supervisor" : "Tester"}
        </span>
        {/* a tester asks only these collections */}
        {a.role === "tester" && (
          <div className={`${styles.kpiNote} mono`} translate="no">
            {(a.collections ?? []).join(", ") || "no collections"}
          </div>
        )}
      </td>
      <td className={styles.nowrap}>
        {a.active ? (
          <span className={`${styles.withIcon} ${styles.ok}`}>
            <StatusOkIcon /> Active
          </span>
        ) : (
          <span className={`${styles.withIcon} ${styles.muted}`}>
            <StatusErrorIcon /> Deactivated
          </span>
        )}
        {a.active && !a.last_login_at && <div className={styles.kpiNote}>hasn&apos;t logged in yet</div>}
      </td>
      <td className={styles.nowrap}>
        {a.last_login_at ? formatDateTime(a.last_login_at) : "never"}
        <div className={styles.kpiNote}>added {formatDateTime(a.created_at)}</div>
      </td>
      <td className={styles.actionsCell}>
        <div className={styles.rowActions}>
          <EditAccountButton
            username={a.username}
            displayName={a.display_name}
            role={a.role}
            collections={collections}
            checked={a.collections ?? []}
          />
          <ResetPasswordButton username={a.username} />
          {a.active ? (
            <ConfirmAction
              label="Deactivate"
              title={`Deactivate ${a.username}?`}
              confirmLabel="Deactivate"
              action={updateAccount.bind(null, a.username, { active: false })}
              done={`${a.username} deactivated`}
            >
              <p>
                {isMe
                  ? "You are logged out at once and can't log in again"
                  : `${a.username} is logged out at once and can't log in`}{" "}
                until a super admin reactivates the account. Their chats stay.
              </p>
            </ConfirmAction>
          ) : (
            <ConfirmAction
              quiet
              label="Reactivate"
              title={`Reactivate ${a.username}?`}
              confirmLabel="Reactivate"
              action={updateAccount.bind(null, a.username, { active: true })}
              done={`${a.username} reactivated`}
            >
              <p>{a.username} can log in again with their current password.</p>
            </ConfirmAction>
          )}
        </div>
      </td>
    </tr>
  );
}
