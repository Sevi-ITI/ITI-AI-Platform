// Companies, decluttered for game-ui like Apps & keys (Vince, 2026-10-28). Not a copy of admin-ui's page any more:
// the same FastAPI calls (check:parity) and the same dialogs and actions (dialogs.tsx, actions.ts, company-list.tsx:
// copies, check:rooms), a calmer card: name and buttons at the top, then plain " | " lines instead of rows of chips
// (its collections, shared with it, its apps, its keys, its HRDotNet database), and quiet links to its keys, users
// and requests.
import Link from "next/link";
import { Fragment } from "react";

import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatCount, formatDateTime, initials } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import ConfirmAction from "../kit/confirm-action";
import styles from "../kit/dashboard.module.css";
import GateBar from "../kit/gate-bar";
import { Problem } from "../kit/widgets";
import { deleteCompany, deleteCompanyDatabase } from "./actions";
import css from "./companies.module.css";
import CompanyList from "./company-list";
import { type AppOption, AddCompanyButton, DatabaseDialog, DatabaseTestButton, EditCompanyButton } from "./dialogs";

export const metadata = { title: "Companies" };

type Company = components["schemas"]["CompanyInfo"];
type Database = components["schemas"]["CompanyDatabaseOut"];

// The systems whose database is per company (backend: app/tools/shared.py COMPANY_DATABASES).
// ponytail: listed here too; serve it from FastAPI when a second system comes.
const SYSTEMS = ["hrdotnet"];

/** "a | b | c" in mono (collection ids), or the words for none */
function idList(names: string[], none: string) {
  return names.length ? (
    <span className="mono" translate="no">
      {names.join(" | ")}
    </span>
  ) : (
    <span className={styles.muted}>{none}</span>
  );
}

// ITI's client companies (ITI itself included): their own collections and how many active keys serve them.
// A company's collections are private to it; Global collections are listed once, at the bottom.
export default async function CompaniesPage() {
  await testersGoToChat(); // testers have only the Chat page
  const [companies, collections, apps, databases, gate, me] = await Promise.all([
    callApi((api) => api.GET("/v1/admin/companies")),
    callApi((api) => api.GET("/v1/admin/collections")),
    callApi((api) => api.GET("/v1/admin/apps")),
    callApi((api) => api.GET("/v1/admin/tools/company-databases")), // 8.6M, super admin only (supervisors: 403)
    callApi((api) => api.GET("/v1/admin/tools/gate")), // changing a database needs the security password
    currentAccount(),
  ]);
  endSessionOn401(companies, collections, apps, databases, gate, me);

  const canEdit = me.ok && me.data.role === "super_admin";
  const locked = !(gate.ok && gate.data.unlocked_until); // FastAPI decides; this only greys out the buttons
  const databasesOf = (companyId: string) => (databases.ok ? databases.data.filter((d) => d.company_id === companyId) : null);
  // apps that can be linked: every app except the console (people log in to it; it has no keys)
  const appOptions: AppOption[] = (apps.ok ? apps.data : [])
    .filter((a) => a.app_id !== "iti-console")
    .map((a) => ({ app_id: a.app_id, name: a.display_name ?? a.app_id }));
  const appNames = new Map(appOptions.map((a) => [a.app_id, a.name]));
  const globals = collections.ok ? collections.data.filter((c) => !c.company_id).map((c) => c.name) : [];

  return (
    <>
      <div className={css.top}>
        <p className={styles.muted}>
          {companies.ok
            ? `${companies.data.length} companies · ${formatCount(companies.data.reduce((n, c) => n + c.active_keys, 0))} active keys · each reaches only its own collections, through keys made for it`
            : ""}
        </p>
        {canEdit && <AddCompanyButton apps={appOptions} />}
      </div>
      {canEdit && gate.ok && <GateBar gate={gate.data} />}

      {!companies.ok ? (
        <Problem message={displayMessage(companies.error)} />
      ) : (
        // ITI itself first, then A to Z, like the console first on Apps & keys
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
              text: [c.name, c.company_id, c.notes, ...c.collections, ...c.shared_collections, ...c.app_ids]
                .filter(Boolean)
                .join(" ")
                .toLowerCase(),
              card: (
                <CompanyCard
                  c={c}
                  canEdit={canEdit}
                  apps={appOptions}
                  appNames={appNames}
                  databases={databasesOf(c.company_id)}
                  locked={locked}
                />
              ),
            }))}
        />
      )}

      <section className={`${styles.card} ${css.globals}`} aria-labelledby="global-title">
        <h2 id="global-title">Global collections</h2>
        <p>{idList(globals, "none yet")}</p>
        <p className={styles.kpiNote}>
          Any company&apos;s key may be given these (e.g. the labor code). Make a collection Global on Documents with
          Move….
        </p>
      </section>
    </>
  );
}

// A company at a glance: who (tile, name, id, added) with its buttons at the top right, what it reaches (plain
// lines), and where to look next (its keys, users, requests: the filters that already exist).
function CompanyCard({
  c,
  canEdit,
  apps,
  appNames,
  databases,
  locked,
}: {
  c: Company;
  canEdit: boolean;
  apps: AppOption[];
  appNames: Map<string, string>;
  databases: Database[] | null; // null = not readable (supervisors)
  locked: boolean;
}) {
  const id = encodeURIComponent(c.company_id);
  return (
    <article className={`${styles.companyCard} ${css.card}`} aria-labelledby={`company-${c.company_id}`}>
      <div className={css.head}>
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
            </span>
            {" | "}added {formatDateTime(c.created_at)}
            {c.company_id === "iti" && " | ITI itself"}
          </p>
        </div>
        {canEdit && (
          <div className={css.buttons}>
            <EditCompanyButton companyId={c.company_id} name={c.name} notes={c.notes} apps={apps} linked={c.app_ids} />
            {c.company_id !== "iti" && (
              <ConfirmAction
                label="Delete"
                title={`Delete ${c.name}?`}
                confirmLabel="Delete company"
                action={deleteCompany.bind(null, c.company_id)}
                done={`${c.name} deleted`}
              >
                <p>
                  Only a company with no collections and no working keys can be deleted; its revoked keys are deleted
                  with it. If something is left, the reason is shown here: delete or move its collections and revoke its
                  apps&apos; keys first.
                </p>
              </ConfirmAction>
            )}
          </div>
        )}
      </div>

      <dl className={css.facts}>
        {c.notes && (
          <>
            <dt>Notes</dt>
            <dd>{c.notes}</dd>
          </>
        )}
        <dt>Collections</dt>
        <dd>{idList(c.collections, "none yet")}</dd>
        {c.shared_collections.length > 0 && (
          <>
            <dt>Shared with it</dt>
            <dd>{idList(c.shared_collections, "")}</dd>
          </>
        )}
        <dt>Apps</dt>
        <dd>
          {c.app_ids.length ? (
            c.app_ids.map((a) => appNames.get(a) ?? a).join(" | ")
          ) : (
            <span className={styles.muted}>none yet: Edit to link one</span>
          )}
        </dd>
        <dt>Keys</dt>
        <dd>
          {c.active_keys > 0 ? (
            <span className={css.activeOn}>{formatCount(c.active_keys)} active</span>
          ) : (
            <span className={styles.muted}>0 active: its people can&apos;t reach the AI yet</span>
          )}
        </dd>
        {databases &&
          SYSTEMS.map((system) => {
            const d = databases.find((x) => x.system === system);
            return (
              <Fragment key={system}>
                <dt>
                  <span className="mono">{system}</span> database
                </dt>
                <dd>
                  <span className={css.dbLine}>
                    {!d ? (
                      <span className={styles.muted}>not set: its people get none of the {system} tools</span>
                    ) : (
                      <>
                        <span className="mono" translate="no">
                          {d.mode === "direct" ? `direct | ${d.url_env}` : `relay | ${d.relay_url} | ${d.token_env}`}
                        </span>
                        {!d.secret_set && <span className={styles.warn}> | not set in backend\.env</span>}
                        {!d.enabled && <span className={styles.muted}> | switched off</span>}
                      </>
                    )}
                  </span>
                  {canEdit && (
                    <span className={css.dbButtons}>
                      <DatabaseDialog companyId={c.company_id} system={system} database={d} locked={locked} />
                      {d && <DatabaseTestButton companyId={c.company_id} system={system} />}
                      {d && (
                        <ConfirmAction
                          locked={locked}
                          label="Remove"
                          title={`Remove the ${system} database of ${c.name}?`}
                          confirmLabel="Remove"
                          action={deleteCompanyDatabase.bind(null, c.company_id, system)}
                          done={`${c.name}: ${system} database removed`}
                        >
                          <p>Its people then get none of the {system} tools. The secret stays in backend\.env.</p>
                        </ConfirmAction>
                      )}
                    </span>
                  )}
                </dd>
              </Fragment>
            );
          })}
      </dl>

      {/* the filters that already exist, opened on this company: quiet links, not buttons */}
      <nav className={css.links} aria-label={`${c.name}: see its`}>
        <span>See its</span>
        <Link href={`/apps?q=${id}`}>keys</Link>
        <span aria-hidden="true">|</span>
        <Link href={`/users?company=${id}`}>users</Link>
        <span aria-hidden="true">|</span>
        <Link href={`/requests?company=${id}`}>requests</Link>
      </nav>
    </article>
  );
}
