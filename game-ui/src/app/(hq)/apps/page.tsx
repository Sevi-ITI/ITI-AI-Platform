// Apps & keys, decluttered for game-ui (Vince, 2026-10-27: "the chips are way too messy per app"). Not a copy of
// admin-ui's page any more: the same FastAPI calls (check:parity) and the same dialogs and actions (dialogs.tsx,
// actions.ts: copies, check:rooms), a calmer layout: the apps in labelled groups; an open card is a short fact list
// (companies and tools as plain text, not chips), New key on its own, the risky buttons at the bottom; one line per
// key with its permissions in words.
import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { formatCount, formatDateTime, formatDay, initials } from "@/lib/format";
import { currentAccount } from "@/lib/session/current-account";
import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import ConfirmAction from "../kit/confirm-action";
import styles from "../kit/dashboard.module.css";
import GateBar from "../kit/gate-bar";
import { StatusErrorIcon, StatusOkIcon, StatusWarnIcon } from "../kit/icons";
import { Problem } from "../kit/widgets";
import { revokeKey } from "./actions";
import AppDetails from "./app-details";
import AppList, { type AppGroup } from "./app-list";
import css from "./apps.module.css";
import { type CollectionOption, usableBy } from "./collection-options";
import {
  CreateAppButton,
  CreateKeyButton,
  EditToolsButton,
  DisconnectAppButton,
  RemoveAppButton,
  EditKeyButton,
  EditProfileButton,
  RotateKeyButton,
  type ToolOption,
} from "./dialogs";

export const metadata = { title: "Apps & keys" };

type App = components["schemas"]["AppOverview"];
type Key = components["schemas"]["KeyInfo"];

// A key's permissions in words (the scopes of the New key presets in dialogs.tsx)
const SCOPE_WORDS: Record<string, string> = {
  "chat:invoke": "Chat",
  "documents:write": "Documents",
  "records:read": "Own records",
  "hrdotnet:read": "HRDotNet records",
  admin: "Admin",
};
const permissions = (scopes: string[]) => scopes.map((s) => SCOPE_WORDS[s] ?? s).join(" + ");

export default async function AppsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  await testersGoToChat(); // testers have only the Chat page
  const { q } = await searchParams;
  const [apps, keys, collections, companies, toolLists, allTools, gate, me] = await Promise.all([
    callApi((api) => api.GET("/v1/admin/apps")),
    callApi((api) => api.GET("/v1/admin/keys")),
    callApi((api) => api.GET("/v1/admin/collections")),
    callApi((api) => api.GET("/v1/admin/companies")),
    // super admin only (supervisors get 403: the tools line is then left out)
    callApi((api) => api.GET("/v1/admin/tools/apps")),
    callApi((api) => api.GET("/v1/admin/tools/tools")),
    callApi((api) => api.GET("/v1/admin/tools/gate")), // 8.6e-3: a tool list needs the security password unlocked
    currentAccount(),
  ]);
  endSessionOn401(apps, keys, collections, companies, toolLists, allTools, gate, me);

  const canEdit = me.ok && me.data.role === "super_admin";
  const collectionOptions: CollectionOption[] = collections.ok
    ? collections.data.map((c) => ({ name: c.name, company_id: c.company_id ?? null, shared_with: c.shared_with }))
    : [];
  const companyNames = new Map((companies.ok ? companies.data : []).map((c) => [c.company_id, c.name]));
  const appTools = toolLists.ok ? new Map(toolLists.data.map((l) => [l.app_id, l.tools])) : null;
  const toolOptions: ToolOption[] | null = allTools.ok
    ? allTools.data.map((t) => ({ name: t.name, scope: t.scope, in_use: t.in_use }))
    : null;
  const toolsLocked = !(gate.ok && gate.data.unlocked_until); // FastAPI decides; this only greys out Edit tools
  const now = new Date().getTime(); // a server component: rendered once per request

  // The console first, then In use, Idle or not used yet, Disconnected (folded); A to Z inside each group.
  const ordered = [...(apps.ok ? apps.data : [])].sort(
    (a, b) =>
      Number(b.app_id === "iti-console") - Number(a.app_id === "iti-console") ||
      usageOf(a, now).rank - usageOf(b, now).rank ||
      (a.display_name ?? a.app_id).localeCompare(b.display_name ?? b.app_id, "en", { sensitivity: "base" }),
  );
  const items = ordered.map((app) => {
    const appKeys = keys.ok ? keys.data.filter((k) => k.app_id === app.app_id) : [];
    const text = [app.app_id, app.display_name, app.owner_name, app.owner_email, app.company, app.description]
      .concat(app.company_ids.flatMap((c) => [c, companyNames.get(c)]))
      .concat(appKeys.flatMap((k) => [k.key_id, k.company_id, companyNames.get(k.company_id)]))
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const usage = usageOf(app, now);
    const group: AppGroup =
      app.app_id === "iti-console" ? "console" : usage.rank === 0 ? "in-use" : usage.rank === 3 ? "disconnected" : "idle";
    return {
      id: app.app_id,
      text,
      group,
      card: (
        <AppCard
          app={app}
          keys={appKeys}
          keysError={keys.ok ? null : displayMessage(keys.error)}
          collections={collectionOptions}
          companyNames={companyNames}
          tools={appTools ? (appTools.get(app.app_id) ?? []) : null}
          toolOptions={toolOptions}
          toolsLocked={toolsLocked}
          canEdit={canEdit}
          now={now}
        />
      ),
    };
  });

  return (
    <>
      <div className={css.top}>
        <p className={styles.muted}>
          {apps.ok ? `${apps.data.length} apps · ${formatCount(keys.ok ? keys.data.filter((k) => isLive(k, now)).length : 0)} active keys` : ""}
        </p>
        {canEdit && apps.ok && <CreateAppButton existing={apps.data.map((a) => a.app_id)} />}
      </div>
      {canEdit && gate.ok && <GateBar gate={gate.data} />}

      {!apps.ok ? (
        <Problem message={displayMessage(apps.error)} />
      ) : apps.data.length === 0 ? (
        <p className={styles.muted}>No apps yet. Create one with New app, link it to a company, then make its key.</p>
      ) : (
        <AppList
          // keyed by ?q=: a city block click with another app starts a fresh search (the box reads ?q= only once)
          key={typeof q === "string" ? q : ""}
          items={items}
          initialQuery={typeof q === "string" ? q : ""}
        />
      )}
    </>
  );
}

/** How the app is doing, in one word (the pill on its closed card); rank = its group in the page order. */
function usageOf(app: App, now: number): { text: string; tone: "ok" | "idle" | "off"; rank: number } {
  if (isDisconnected(app)) return { text: "Disconnected", tone: "off", rank: 3 };
  if (app.active_keys === 0 && app.app_id !== "iti-console") return { text: "No active key", tone: "idle", rank: 2 };
  if (app.last_used_at !== null && now - Date.parse(app.last_used_at) < RECENT_DAYS * 86_400_000)
    return { text: "In use", tone: "ok", rank: 0 };
  if (app.last_used_at !== null) return { text: "Idle", tone: "idle", rank: 1 };
  return { text: "Not used yet", tone: "idle", rank: 2 };
}

/** Disconnect removes the profile, so: no active key and no profile = disconnected. A created app (New app) has a
 * profile and waits for its first key in the main list. */
function isDisconnected(app: App) {
  return app.active_keys === 0 && app.profile_updated_at === null && app.app_id !== "iti-console";
}

// An app counts as recently used (its card starts open) when a key was used within this many days.
const RECENT_DAYS = 7;

function isLive(k: Key, now: number) {
  return !k.revoked_at && (k.expires_at === null || Date.parse(k.expires_at) > now);
}

/** "10 hrdotnet tools, 3 records tools": an app's tool list by source, instead of one chip per tool. */
function toolSummary(tools: { name: string; missing: boolean }[]): string {
  const bySource = new Map<string, number>();
  for (const t of tools) {
    const source = t.name.includes("__") ? t.name.split("__")[0] : "records";
    bySource.set(source, (bySource.get(source) ?? 0) + 1);
  }
  return [...bySource.entries()].map(([source, n]) => `${n} ${source} ${n === 1 ? "tool" : "tools"}`).join(", ");
}

function AppCard({
  app,
  keys,
  keysError,
  collections,
  companyNames,
  tools,
  toolOptions,
  toolsLocked,
  canEdit,
  now,
}: {
  app: App;
  keys: Key[];
  keysError: string | null;
  collections: CollectionOption[];
  companyNames: Map<string, string>;
  tools: { name: string; missing: boolean }[] | null; // its tool list; null = not shown
  toolOptions: ToolOption[] | null;
  toolsLocked: boolean;
  canEdit: boolean;
  now: number;
}) {
  const usage = usageOf(app, now);
  const recent = app.app_id === "iti-console" || usage.tone === "ok";
  const name = app.display_name ?? app.app_id;
  const isConsole = app.app_id === "iti-console";
  const about = [app.description, app.company, app.owner_name && `owner ${app.owner_name}`, app.owner_email]
    .filter(Boolean)
    .join(" | ");
  const missing = tools?.filter((t) => t.missing) ?? [];
  const canDisconnect = !isConsole && (app.active_keys > 0 || app.profile_updated_at || app.users > 0);
  const canRemove = !isConsole && app.active_keys === 0 && app.users === 0;

  return (
    <AppDetails
      defaultOpen={recent}
      summary={
        // closed card, read top-down: who (tile, name, id / company), how much (three numbers), state (pill)
        <>
          <span className={styles.appAvatar} aria-hidden="true">
            {initials(name)}
          </span>
          <span className={styles.appMain}>
            <span className={styles.appName}>{name}</span>
            <span className={styles.appMeta}>
              {app.display_name && (
                <span className="mono" translate="no">
                  {app.app_id}
                </span>
              )}
              {app.display_name && app.company && " · "}
              {app.company}
            </span>
            <span className={styles.appStats}>
              <span>
                <b>{formatCount(app.users)}</b> {app.users === 1 ? "user" : "users"}
              </span>
              <span>
                <b>{formatCount(app.active_keys)}</b> active {app.active_keys === 1 ? "key" : "keys"}
              </span>
              <span>
                last used <b>{app.last_used_at ? formatDateTime(app.last_used_at) : "never"}</b>
              </span>
            </span>
          </span>
          <span className={`${styles.appUsage} ${styles[`appUsage_${usage.tone}`]}`}>
            {usage.tone === "ok" && <StatusOkIcon />}
            {usage.text}
          </span>
        </>
      }
    >
      {/* the facts as plain lines (were rows of chips), the app's buttons at the top right beside them */}
      <div className={css.cardTop}>
      <dl className={css.facts}>
        {about && (
          <>
            <dt>About</dt>
            <dd>{about}</dd>
          </>
        )}
        {app.notes && (
          <>
            <dt>Notes</dt>
            <dd>{app.notes}</dd>
          </>
        )}
        {!isConsole && (
          <>
            <dt>Companies</dt>
            <dd>
              {app.company_ids.length ? (
                app.company_ids.map((c) => companyNames.get(c) ?? c).join(" | ")
              ) : (
                <span className={styles.muted}>none yet: link it on Companies before making a key</span>
              )}
            </dd>
          </>
        )}
        {!isConsole && tools && (
          <>
            <dt>Tools</dt>
            <dd>
              {tools.length ? (
                <details className={css.inlineFold}>
                  <summary>
                    {toolSummary(tools)}
                    {missing.length > 0 && <span className={styles.warn}> · {missing.length} missing</span>}
                  </summary>
                  <span className={`mono ${css.toolNames}`} translate="no">
                    {tools.map((t) => `${t.name.split("__").pop()}${t.missing ? " (missing)" : ""}`).join(", ")}
                  </span>
                </details>
              ) : (
                <span className={styles.muted}>none: its keys answer from documents only</span>
              )}
            </dd>
          </>
        )}
        {isConsole && (
          <>
            <dt>Keys</dt>
            <dd className={styles.muted}>none: people log in to the console with their accounts</dd>
          </>
        )}
      </dl>

      {canEdit && (
        <div className={css.actions}>
          {!isConsole && (
            <CreateKeyButton
              appId={app.app_id}
              companies={app.company_ids.map((c) => ({ company_id: c, name: companyNames.get(c) ?? c }))}
              collections={collections}
            />
          )}
          {!isConsole && tools && toolOptions && (
            <EditToolsButton
              appId={app.app_id}
              tools={toolOptions}
              checked={tools.map((t) => t.name)}
              missing={missing.map((t) => t.name)}
              locked={toolsLocked}
            />
          )}
          <EditProfileButton appId={app.app_id} profile={app} />
        </div>
      )}
      </div>

      {/* the keys: one line each, under the company it serves */}
      {keysError ? (
        <Problem message={keysError} />
      ) : (
        !isConsole &&
        (keys.length === 0 ? (
          <p className={styles.muted}>
            {app.company_ids.length ? "No keys yet: make one with New key." : "No keys yet: link this app to a company first."}
          </p>
        ) : (
          [...new Set(keys.map((k) => k.company_id))]
            .sort((a, b) => (companyNames.get(a) ?? a).localeCompare(companyNames.get(b) ?? b))
            .map((companyId) => {
              const companyKeys = keys.filter((k) => k.company_id === companyId);
              const live = companyKeys.filter((k) => isLive(k, now));
              // expired (Edit can renew one) and revoked (can't come back) keys: folded, kept as history
              const old = companyKeys.filter((k) => !isLive(k, now));
              const expired = old.filter((k) => !k.revoked_at).length;
              return (
                <div key={companyId} className={css.keyGroup}>
                  <h3 className={css.keyGroupTitle}>
                    Keys for {companyNames.get(companyId) ?? companyId}
                    <span className={live.length ? `${css.activeCount} ${css.activeOn}` : css.activeCount}>
                      {live.length} active
                    </span>
                  </h3>
                  {live.length > 0 && (
                    <ul className={css.keys}>
                      {live.map((k) => (
                        <KeyRow key={k.key_id} k={k} collections={usableBy(collections, k.company_id)} canEdit={canEdit} now={now} />
                      ))}
                    </ul>
                  )}
                  {old.length > 0 && (
                    <details className={css.inlineFold}>
                      <summary>
                        {[expired && `${expired} expired`, old.length - expired && `${old.length - expired} revoked`]
                          .filter(Boolean)
                          .join(", ")}{" "}
                        {old.length === 1 ? "key" : "keys"}
                      </summary>
                      <ul className={css.keys}>
                        {old.map((k) => (
                          <KeyRow key={k.key_id} k={k} collections={usableBy(collections, k.company_id)} canEdit={canEdit} now={now} />
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              );
            })
        ))
      )}

      {/* the risky ones last, set apart */}
      {canEdit && (canDisconnect || canRemove) && (
        <div className={css.danger}>
          <span className={styles.kpiNote}>Stop this app</span>
          {canDisconnect && (
            <DisconnectAppButton
              appId={app.app_id}
              users={app.users}
              activeKeys={app.active_keys}
              hasAdminKey={keys.some(
                (k) => k.scopes.includes("admin") && !k.revoked_at && (!k.expires_at || Date.parse(k.expires_at) > now),
              )}
            />
          )}
          {canRemove && <RemoveAppButton appId={app.app_id} keys={keys.length} />}
        </div>
      )}
    </AppDetails>
  );
}

/** One key on one line: id, permissions in words, how many collections, state, use, and its buttons. */
function KeyRow({ k, collections, canEdit, now }: { k: Key; collections: CollectionOption[]; canEdit: boolean; now: number }) {
  const expired = k.expires_at !== null && Date.parse(k.expires_at) <= now;
  const active = !k.revoked_at && !expired;
  const n = k.allowed_collections.length;
  return (
    <li className={`${css.key} ${active ? "" : styles.dimmed}`}>
      <div className={css.keyMain}>
        <span className="mono" translate="no" title={`Created ${formatDateTime(k.created_at)}`}>
          {k.key_id}
        </span>
        <span className={css.keyWhat}>
          {permissions(k.scopes)}
          <span className={styles.muted}>
            {" · "}
            <span title={k.allowed_collections.join(", ")}>{n ? `${n} ${n === 1 ? "collection" : "collections"}` : "no collections"}</span>
          </span>
        </span>
      </div>
      <div className={css.keyState}>
        {k.revoked_at ? (
          <span className={`${styles.withIcon} ${styles.muted}`}>
            <StatusErrorIcon /> Revoked {formatDay(k.revoked_at)}
          </span>
        ) : expired ? (
          <span className={`${styles.withIcon} ${styles.warn}`}>
            <StatusWarnIcon /> Expired {formatDay(k.expires_at!)}
          </span>
        ) : (
          <span className={`${styles.withIcon} ${styles.ok}`}>
            <StatusOkIcon /> Active
          </span>
        )}
        <span className={styles.kpiNote}>
          {k.last_used_at ? `used ${formatDateTime(k.last_used_at)}` : "never used"} · {formatCount(k.requests_24h)} in 24 h
          {active && (k.expires_at ? ` · expires ${formatDay(k.expires_at)}` : "")}
        </span>
      </div>
      {canEdit && !k.revoked_at && (
        <div className={css.keyActions}>
          {/* an expired key can be renewed here (new expiry); a revoked one can't come back */}
          <EditKeyButton
            keyId={k.key_id}
            company={k.company_id}
            collections={collections}
            current={k.allowed_collections}
            expiresLabel={k.expires_at ? `${expired ? "expired" : "expires"} ${formatDay(k.expires_at)}` : "never expires"}
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
              <span className="mono">{k.key_id}</span> ({k.app_id}) stops working at once: every request with it gets
              &quot;invalid API key&quot;. This can&apos;t be undone; the app needs a new key.
            </p>
          </ConfirmAction>
        </div>
      )}
    </li>
  );
}
