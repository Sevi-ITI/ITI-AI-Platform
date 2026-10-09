import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";

import ConfirmAction from "../confirm-action";
import styles from "../dashboard.module.css";
import Placeholder from "../placeholder";
import { Problem } from "../widgets";
import { updateAccount } from "./actions";
import { AddAccountButton, EditAccountButton, ResetPasswordButton } from "./dialogs";

export const metadata = { title: "Accounts" };

// Console accounts (super admin only): who can log in, with which role. FastAPI refuses everyone else,
// and refuses a change that would leave no active super admin (409 last_super_admin).
export default async function AccountsPage() {
  const me = await currentAccount();
  endSessionOn401(me);
  if (!me.ok || me.data.role !== "super_admin") {
    return (
      <Placeholder title="Accounts" step="Super admin only">
        Only a super admin can see and manage console accounts. (FastAPI refuses these requests for anyone else.)
      </Placeholder>
    );
  }

  const accounts = await callApi((api) => api.GET("/v1/admin/accounts"));
  endSessionOn401(accounts);

  return (
    <>
      <header className={styles.header}>
        <h1>Accounts</h1>
        <AddAccountButton />
      </header>

      <section className={styles.card} aria-label="Console accounts">
        {!accounts.ok ? (
          <Problem message={displayMessage(accounts.error)} />
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">Username</th>
                  <th scope="col">Role</th>
                  <th scope="col">State</th>
                  <th scope="col" className={styles.nowrap}>
                    Last login
                  </th>
                  <th scope="col">Added</th>
                  <th scope="col">{/* actions */}</th>
                </tr>
              </thead>
              <tbody>
                {accounts.data.map((a) => {
                  const isMe = a.username === me.data.username;
                  return (
                    <tr key={a.username} className={a.active ? undefined : styles.dimmed}>
                      <td>
                        {a.display_name ?? "–"}
                        {isMe && <span className={styles.muted}> (you)</span>}
                      </td>
                      <td className={`mono ${styles.nowrap}`} translate="no">
                        {a.username}
                      </td>
                      <td className={styles.nowrap}>{a.role === "super_admin" ? "Super admin" : "Supervisor"}</td>
                      <td className={styles.nowrap}>
                        {a.active ? (
                          <span className={styles.ok}>● Active</span>
                        ) : (
                          <span className={styles.muted}>○ Deactivated</span>
                        )}
                      </td>
                      <td className={styles.nowrap}>{a.last_login_at ? formatDateTime(a.last_login_at) : "never"}</td>
                      <td className={styles.nowrap}>{formatDateTime(a.created_at)}</td>
                      <td>
                        <div className={styles.rowActions}>
                          <EditAccountButton username={a.username} displayName={a.display_name} role={a.role} />
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
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
