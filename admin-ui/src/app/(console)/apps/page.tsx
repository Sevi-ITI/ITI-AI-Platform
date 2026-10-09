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

// Every connected system (from its keys, its chats or a profile): profile, live counts and its keys, with a search
// box. Apps with no active key (except the console) are "Disconnected": kept as history, folded at the bottom.
// Changes (create / rotate / revoke / edit a key, edit a profile, disconnect) are the super admin's.
export default async function AppsPage() {
  const [apps, keys, collections, me] = await Promise.all([
    callApi((api) => api.GET("/v1/admin/apps")),
    callApi((api) => api.GET("/v1/admin/keys")),
    callApi((api) => api.GET("/v1/admin/collections")),
    currentAccount(),
  ]);
  endSessionOn401(apps, keys, collections, me);

  const canEdit = me.ok && me.data.role === "super_admin";
  const collectionNames = collections.ok ? collections.data.map((c) => c.name) : [];
  const now = new Date().getTime(); // a server component: rendered once per request

  // Each card with the text it can be searched by (lowercase): app id, profile fields, key ids.
  const items = (apps.ok ? apps.data : []).map((app) => {
    const appKeys = keys.ok ? keys.data.filter((k) => k.app_id === app.app_id) : [];
    const text = [app.app_id, app.display_name, app.owner_name, app.owner_email, app.company, app.description]
      .concat(appKeys.map((k) => k.key_id))
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
          collections={collectionNames}
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
        {canEdit && apps.ok && <CreateKeyButton apps={apps.data.map((a) => a.app_id)} collections={collectionNames} />}
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
  canEdit,
  now,
}: {
  app: App;
  keys: Key[];
  keysError: string | null;
  collections: string[];
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
              {keys.map((k) => (
                <KeyRow key={k.key_id} k={k} collections={collections} canEdit={canEdit} now={now} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function KeyRow({ k, collections, canEdit, now }: { k: Key; collections: string[]; canEdit: boolean; now: number }) {
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
