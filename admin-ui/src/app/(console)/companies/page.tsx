import Link from "next/link";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatCount, formatDateTime, initials } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";

import ConfirmAction from "../confirm-action";
import styles from "../dashboard.module.css";
import { Problem } from "../widgets";
import { deleteCompany } from "./actions";
import CompanyList from "./company-list";
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

      {!companies.ok ? (
        <Problem message={displayMessage(companies.error)} />
      ) : (
        // One card per company (was a table whose link and action columns ran off the right edge). ITI itself first,
        // then A to Z, like the console first on Apps & keys.
        <CompanyList
          items={[...companies.data]
            .sort(
              (a, b) =>
                Number(b.company_id === "iti") - Number(a.company_id === "iti") ||
                a.name.localeCompare(b.name, "en", { sensitivity: "base" }),
            )
            .map((c) => ({
              id: c.company_id,
              // what the search box can find it by (lowercase)
              text: [c.name, c.company_id, c.notes, ...c.collections, ...c.shared_collections]
                .filter(Boolean)
                .join(" ")
                .toLowerCase(),
              card: <CompanyCard c={c} canEdit={canEdit} />,
            }))}
        />
      )}

      <section className={styles.card} aria-labelledby="global-title">
        <h2 id="global-title" className={styles.panelTitle}>
          Global collections
        </h2>
        <p className={styles.tags}>
          {globals.length
            ? globals.map((name) => (
                <span key={name} className={`${styles.tag} mono`} translate="no">
                  {name}
                </span>
              ))
            : "None yet."}
        </p>
        <p className={styles.muted}>
          Any company&apos;s key may be given these (e.g. the labor code). Make a collection Global on the Documents
          page with Move….
        </p>
      </section>
    </>
  );
}

type Company = components["schemas"]["CompanyInfo"];

// A company at a glance: who (tile, name, id, added, notes), what it reaches (its collections, those shared with it,
// active keys), and where to look next (its keys, users, requests: the filters that already exist).
function CompanyCard({ c, canEdit }: { c: Company; canEdit: boolean }) {
  const id = encodeURIComponent(c.company_id);
  return (
    <article className={styles.companyCard} aria-labelledby={`company-${c.company_id}`}>
      <div className={styles.companyHead}>
        <span className={styles.appAvatar} aria-hidden="true">
          {initials(c.name)}
        </span>
        <div className={styles.appMain}>
          <h2 id={`company-${c.company_id}`} className={styles.appName}>
            {c.name}
          </h2>
          <p className={styles.appMeta}>
            <span className="mono" translate="no">
              {c.company_id}
            </span>{" "}
            · added {formatDateTime(c.created_at)}
            {c.company_id === "iti" && " · ITI itself"}
          </p>
        </div>
        {canEdit && (
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
                  Only a company with no collections and no keys (of any state) can be deleted. If it still has some, the
                  reason is shown here: delete or move its collections and remove its apps&apos; keys first.
                </p>
              </ConfirmAction>
            )}
          </div>
        )}
      </div>

      {c.notes && <p className={styles.muted}>{c.notes}</p>}

      <dl className={styles.companyFacts}>
        <div>
          <dt>Its collections</dt>
          <dd className={styles.tags}>
            {c.collections.length ? (
              c.collections.map((name) => (
                <span key={name} className={`${styles.tag} mono`} translate="no">
                  {name}
                </span>
              ))
            ) : (
              <span className={styles.muted}>none yet</span>
            )}
          </dd>
        </div>
        {c.shared_collections.length > 0 && (
          <div>
            <dt>Shared with it</dt>
            <dd className={styles.tags}>
              {c.shared_collections.map((name) => (
                <span key={name} className={`${styles.tag} mono`} translate="no">
                  {name}
                </span>
              ))}
            </dd>
          </div>
        )}
        <div>
          <dt>Active keys</dt>
          <dd>
            <b className={styles.num}>{formatCount(c.active_keys)}</b>
            {c.active_keys === 0 && <span className={styles.muted}> (its people can&apos;t reach the AI yet)</span>}
          </dd>
        </div>
      </dl>

      {/* the filters that already exist, opened on this company */}
      <nav className={styles.companyLinks} aria-label={`${c.name}: see its`}>
        <span className={styles.muted}>See its</span>
        <Link href={`/apps?q=${id}`} className={styles.smallButton}>
          Keys →
        </Link>
        <Link href={`/users?company=${id}`} className={styles.smallButton}>
          Users →
        </Link>
        <Link href={`/requests?company=${id}`} className={styles.smallButton}>
          Requests →
        </Link>
      </nav>
    </article>
  );
}

