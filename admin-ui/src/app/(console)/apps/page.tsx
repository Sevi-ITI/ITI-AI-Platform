import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatCount, formatDateTime, formatDay } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";

import ConfirmAction from "../confirm-action";
import styles from "../dashboard.module.css";
import { Problem } from "../widgets";
import { revokeKey } from "./actions";
import AppList from "./app-list";
import { type CollectionOption, usableBy } from "./collection-options";
import {
  CreateKeyButton,
  DisconnectAppButton,
  RemoveAppButton,
  EditKeyButton,
  EditProfileButton,
  RotateKeyButton,
} from "./dialogs";

export const metadata = { title: "Apps & keys" };

type App = components["schemas"]["AppOverview"];
type Key = components["schemas"]["KeyInfo"];

// Every connected system (from its keys, its chats or a profile): profile, live counts and its keys grouped by the
// client company each key serves (App -> Company -> Keys), with a search box. Apps with no active key (except the console) are "Disconnected": kept as history, folded at the bottom.
// Changes (create / rotate / revoke / edit a key, edit a profile, disconnect) are the super admin's.
export default async function AppsPage() {
  const [apps, keys, collections, companies, me] = await Promise.all([
    callApi((api) => api.GET("/v1/admin/apps")),
    callApi((api) => api.GET("/v1/admin/keys")),
    callApi((api) => api.GET("/v1/admin/collections")),
    callApi((api) => api.GET("/v1/admin/companies")),
    currentAccount(),
  ]);
  endSessionOn401(apps, keys, collections, companies, me);

  const canEdit = me.ok && me.data.role === "super_admin";
  const collectionOptions: CollectionOption[] = collections.ok
    ? collections.data.map((c) => ({ name: c.name, company_id: c.company_id ?? null }))
    : [];
  const companyNames = new Map((companies.ok ? companies.data : []).map((c) => [c.company_id, c.name]));
  const now = new Date().getTime(); // a server component: rendered once per request

  // Each card with the text it can be searched by (lowercase): app id, profile fields, key ids.
  const items = (apps.ok ? apps.data : []).map((app) => {
    const appKeys = keys.ok ? keys.data.filter((k) => k.app_id === app.app_id) : [];
    const text = [app.app_id, app.display_name, app.owner_name, app.owner_email, app.company, app.description]
      .concat(appKeys.flatMap((k) => [k.key_id, k.company_id, companyNames.get(k.company_id)]))
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return {
      id: app.app_id,
      text,
      disconnected: app.active_keys === 0 && app.app_id !== "iti-console",
      card: (
        <AppCard
          app={app}
          keys={appKeys}
          keysError={keys.ok ? null : displayMessage(keys.error)}
          collections={collectionOptions}
          companyNames={companyNames}
          canEdit={canEdit}
          now={now}
        />
      ),
    };
  });

  return (
    <>
      <header className={styles.header}>
        <h1>Apps &amp; keys</h1>
        {canEdit && apps.ok && (
          <CreateKeyButton
            apps={apps.data.map((a) => a.app_id)}
            companies={companies.ok ? companies.data.map((c) => ({ company_id: c.company_id, name: c.name })) : []}
            collections={collectionOptions}
          />
        )}
      </header>

      {!apps.ok ? (
        <Problem message={displayMessage(apps.error)} />
      ) : apps.data.length === 0 ? (
        <p className={styles.muted}>No apps yet. Create a key to connect the first one.</p>
      ) : (
        <AppList active={items.filter((it) => !it.disconnected)} disconnected={items.filter((it) => it.disconnected)} />
      )}
    </>
  );
}

function AppCard({
  app,
  keys,
  keysError,
  collections,
  companyNames,
  canEdit,
  now,
}: {
  app: App;
  keys: Key[];
  keysError: string | null;
  collections: CollectionOption[];
  companyNames: Map<string, string>;
  canEdit: boolean;
  now: number;
}) {
  const details = [app.description, app.company, app.owner_name && `Owner: ${app.owner_name}`, app.owner_email]
    .filter(Boolean)
    .join(" · ");

  return (
    <section className={styles.card} aria-label={app.display_name ?? app.app_id}>
      <div className={styles.cardHead}>
        <div>
          <h2>
            {app.display_name ?? app.app_id}{" "}
            {app.display_name && (
              <span className={`mono ${styles.muted}`} translate="no">
                {app.app_id}
              </span>
            )}
          </h2>
          {details && <p className={styles.muted}>{details}</p>}
          {app.notes && <p className={styles.muted}>{app.notes}</p>}
        </div>
        {canEdit && (
          <div className={styles.rowActions}>
            <EditProfileButton appId={app.app_id} profile={app} />
            {/* only when it would change something: an active key, a profile, or users' chats to erase */}
            {app.app_id !== "iti-console" && (app.active_keys > 0 || app.profile_updated_at || app.users > 0) && (
              <DisconnectAppButton
                appId={app.app_id}
                users={app.users}
                activeKeys={app.active_keys}
                hasAdminKey={keys.some(
                  (k) =>
                    k.scopes.includes("admin") && !k.revoked_at && (!k.expires_at || Date.parse(k.expires_at) > now),
                )}
              />
            )}
            {/* a disconnected app with no chats left can go for good */}
            {app.app_id !== "iti-console" && app.active_keys === 0 && app.users === 0 && (
              <RemoveAppButton appId={app.app_id} keys={keys.length} />
            )}
          </div>
        )}
      </div>
      <p className={styles.muted}>
        {formatCount(app.users)} {app.users === 1 ? "user" : "users"} · {formatCount(app.active_keys)} active{" "}
        {app.active_keys === 1 ? "key" : "keys"} · last used{" "}
        {app.last_used_at ? formatDateTime(app.last_used_at) : "never"}
      </p>

      {keysError ? (
        <Problem message={keysError} />
      ) : keys.length === 0 ? (
        <p className={styles.muted}>
          {app.app_id === "iti-console"
            ? "The console itself: people log in with their accounts, no keys."
            : "No keys (this app only appears because of its chats or profile)."}
        </p>
      ) : (
        // one small table per client company, alphabetical by company name
        [...new Set(keys.map((k) => k.company_id))]
          .sort((a, b) => (companyNames.get(a) ?? a).localeCompare(companyNames.get(b) ?? b))
          .map((companyId) => {
            const companyKeys = keys.filter((k) => k.company_id === companyId);
            const live = companyKeys.filter((k) => isLive(k, now));
            const mayUse = [...new Set(live.flatMap((k) => k.allowed_collections))].sort();
            return (
              <div key={companyId} className={styles.companyGroup}>
                <h3>
                  {companyNames.get(companyId) ?? companyId}{" "}
                  <span className={`mono ${styles.muted}`} translate="no">
                    {companyId}
                  </span>
                </h3>
                <p className={styles.muted}>
                  May use:{" "}
                  {mayUse.length ? <span className="mono">{mayUse.join(", ")}</span> : "nothing (no active key)"}
                </p>
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th scope="col">Key</th>
                        <th scope="col">Permissions</th>
                        <th scope="col">Collections</th>
                        <th scope="col">State</th>
                        <th scope="col" className={styles.nowrap}>
                          Last used
                        </th>
                        <th scope="col" className={styles.number}>
                          24 h
                        </th>
                        {canEdit && <th scope="col">{/* actions */}</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {companyKeys.map((k) => (
                        <KeyRow
                          key={k.key_id}
                          k={k}
                          collections={usableBy(collections, k.company_id)}
                          canEdit={canEdit}
                          now={now}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })
      )}
    </section>
  );
}

function isLive(k: Key, now: number) {
  return !k.revoked_at && (k.expires_at === null || Date.parse(k.expires_at) > now);
}

function KeyRow({
  k,
  collections,
  canEdit,
  now,
}: {
  k: Key;
  collections: CollectionOption[];
  canEdit: boolean;
  now: number;
}) {
  const expired = k.expires_at !== null && Date.parse(k.expires_at) <= now;
  const active = !k.revoked_at && !expired;
  const expiresLabel = k.expires_at ? `expires ${formatDay(k.expires_at)}` : "never expires";

  return (
    <tr className={active ? undefined : styles.dimmed}>
      <td className={`mono ${styles.nowrap}`} translate="no" title={`Created ${formatDateTime(k.created_at)}`}>
        {k.key_id}
      </td>
      <td className="mono">{k.scopes.join(", ")}</td>
      <td className="mono">{k.allowed_collections.length ? k.allowed_collections.join(", ") : "–"}</td>
      <td className={styles.nowrap}>
        {k.revoked_at ? (
          <span className={styles.muted}>✕ Revoked {formatDay(k.revoked_at)}</span>
        ) : expired ? (
          <span className={styles.warn}>○ Expired {formatDay(k.expires_at!)}</span>
        ) : (
          <span className={styles.ok}>
            ● Active <span className={styles.muted}>({expiresLabel})</span>
          </span>
        )}
      </td>
      <td className={styles.nowrap}>{k.last_used_at ? formatDateTime(k.last_used_at) : "never"}</td>
      <td className={styles.number}>{formatCount(k.requests_24h)}</td>
      {canEdit && (
        <td>
          {!k.revoked_at && (
            <div className={styles.rowActions}>
              {/* an expired key can be renewed here (new expiry); a revoked one can't come back */}
              <EditKeyButton
                keyId={k.key_id}
                collections={collections}
                current={k.allowed_collections}
                expiresLabel={
                  k.expires_at ? `${expired ? "expired" : "expires"} ${formatDay(k.expires_at)}` : "never expires"
                }
              />
              <RotateKeyButton keyId={k.key_id} appId={k.app_id} />
              <ConfirmAction
                label="Revoke"
                title="Revoke this key?"
                confirmLabel="Revoke key"
                action={revokeKey.bind(null, k.key_id)}
                done={`Key ${k.key_id} revoked`}
              >
                <p>
                  <span className="mono">{k.key_id}</span> ({k.app_id}) stops working at once: every request with it
                  gets &quot;invalid API key&quot;. This can&apos;t be undone; the app needs a new key.
                </p>
              </ConfirmAction>
            </div>
          )}
        </td>
      )}
    </tr>
  );
}
