import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import { formatCount, formatDateTime } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";

import ConfirmAction from "../confirm-action";
import styles from "../dashboard.module.css";
import { Problem } from "../widgets";
import { deleteCompany } from "./actions";
import { AddCompanyButton, EditCompanyButton } from "./dialogs";

export const metadata = { title: "Companies" };

// ITI's client companies (ITI itself included): their own collections and how many active keys serve them.
// A company's collections are private to it; Global collections are listed once, at the bottom.
export default async function CompaniesPage() {
  const [companies, collections, me] = await Promise.all([
    callApi((api) => api.GET("/v1/admin/companies")),
    callApi((api) => api.GET("/v1/admin/collections")),
    currentAccount(),
  ]);
  endSessionOn401(companies, collections, me);

  const canEdit = me.ok && me.data.role === "super_admin";
  const globals = collections.ok ? collections.data.filter((c) => !c.company_id).map((c) => c.name) : [];

  return (
    <>
      <header className={styles.header}>
        <h1>Companies</h1>
        {canEdit && <AddCompanyButton />}
      </header>
      <p className={styles.muted}>
        Each client company has its own collections; its people reach them only through keys made for that company.
      </p>

      <section className={styles.card} aria-label="Companies">
        {!companies.ok ? (
          <Problem message={displayMessage(companies.error)} />
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">Company</th>
                  <th scope="col">Its collections</th>
                  <th scope="col" className={styles.number}>
                    Active keys
                  </th>
                  <th scope="col">Added</th>
                  {canEdit && <th scope="col">{/* actions */}</th>}
                </tr>
              </thead>
              <tbody>
                {companies.data.map((c) => (
                  <tr key={c.company_id}>
                    <td>
                      {c.name}{" "}
                      <span className={`mono ${styles.muted}`} translate="no">
                        {c.company_id}
                      </span>
                      {c.notes && <div className={styles.muted}>{c.notes}</div>}
                    </td>
                    <td className="mono">{c.collections.length ? c.collections.join(", ") : "–"}</td>
                    <td className={styles.number}>{formatCount(c.active_keys)}</td>
                    <td className={styles.nowrap}>{formatDateTime(c.created_at)}</td>
                    {canEdit && (
                      <td>
                        <div className={styles.rowActions}>
                          <EditCompanyButton companyId={c.company_id} name={c.name} notes={c.notes} />
                          {c.company_id !== "iti" && (
                            <ConfirmAction
                              label="Delete"
                              title={`Delete ${c.name}?`}
                              confirmLabel="Delete company"
                              action={deleteCompany.bind(null, c.company_id)}
                              done={`${c.name} deleted`}
                            >
                              <p>
                                Only a company with no collections and no keys (of any state) can be deleted. If it
                                still has some, the reason is shown here: delete or move its collections and remove its
                                apps&apos; keys first.
                              </p>
                            </ConfirmAction>
                          )}
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <p className={styles.muted}>
        Global collections (any company&apos;s key may be given them):{" "}
        {globals.length ? <span className="mono">{globals.join(", ")}</span> : "none yet"}. Make one Global on the
        Documents page (Move…).
      </p>
    </>
  );
}
