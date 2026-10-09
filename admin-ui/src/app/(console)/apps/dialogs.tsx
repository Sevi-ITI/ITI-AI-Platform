"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import type { components } from "@/lib/api/schema";

import dash from "../dashboard.module.css";
import { toast } from "../toast";
import { createKey, disconnectApp, editKey, removeApp, rotateKey, saveProfile, type NewKey } from "./actions";

// The super admin's buttons on Apps & keys, each with its own native <dialog>. A new key's secret lives only
// in this component's state while its dialog is open; closing the dialog drops it.

type Profile = components["schemas"]["AppProfileIn"];
type Scope = components["schemas"]["KeyCreate"]["scopes"][number];

const PRESETS: { id: string; label: string; scopes: Scope[] }[] = [
  { id: "chat", label: "Chat app (ask questions)", scopes: ["chat:invoke"] },
  {
    id: "chat-docs",
    label: "Chat + documents app (ask, upload, replace, delete)",
    scopes: ["chat:invoke", "documents:write"],
  },
  { id: "uploader", label: "Document uploader (upload, replace, delete)", scopes: ["documents:write"] },
  { id: "admin", label: "Admin (full control of the AI system)", scopes: ["admin"] },
];

function useErrorRedirect() {
  const router = useRouter();
  // 401 = session over; anything else is shown in the dialog
  return (r: { ok: false; status: number; message: string }) =>
    r.status === 401 ? (router.push("/login"), null) : r.message;
}

/** The new key, shown once with a copy button. */
function NewKeyPanel({ result }: { result: Extract<NewKey, { ok: true }> }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className={dash.field}>
      <span>New key (shown once: copy it now)</span>
      <input
        className="mono"
        readOnly
        value={result.apiKey}
        onFocus={(e) => e.currentTarget.select()}
        aria-label="New API key"
      />
      <button
        type="button"
        className={dash.secondary}
        onClick={() => void navigator.clipboard.writeText(result.apiKey).then(() => setCopied(true))}
      >
        {copied ? "✓ Copied" : "Copy key"}
      </button>
      <small>
        Put it in the app&apos;s server configuration, never in a browser or a repository. It can&apos;t be shown again;
        if it&apos;s lost, rotate the key.
      </small>
      {result.warning && (
        <p role="alert" className={dash.error}>
          {result.warning}
        </p>
      )}
    </div>
  );
}

function CollectionChecks({ collections, checked }: { collections: string[]; checked: string[] }) {
  return (
    <fieldset className={dash.checks}>
      <legend>Collections it may use</legend>
      {collections.map((c) => (
        <label key={c} className={dash.check}>
          <input type="checkbox" name="collections" value={c} defaultChecked={checked.includes(c)} />
          <span className="mono">{c}</span>
        </label>
      ))}
    </fieldset>
  );
}

export function CreateKeyButton({ apps, collections }: { apps: string[]; collections: string[] }) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const toMessage = useErrorRedirect();
  const [preset, setPreset] = useState(PRESETS[0].id);
  const [never, setNever] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [made, setMade] = useState<Extract<NewKey, { ok: true }> | null>(null);
  const scopes = PRESETS.find((p) => p.id === preset)!.scopes;
  const isAdmin = scopes.includes("admin");

  async function submit(form: HTMLFormElement) {
    const data = new FormData(form);
    setBusy(true);
    setError(null);
    const r = await createKey({
      app_id: String(data.get("app_id") ?? "").trim(),
      scopes,
      allowed_collections: isAdmin ? [] : data.getAll("collections").map(String),
      valid_days: never ? null : Number(data.get("days")),
    });
    setBusy(false);
    if (r.ok) {
      setMade(r);
      toast("ok", `Key ${r.keyId} created: copy it now`);
      router.refresh();
    } else {
      setError(toMessage(r));
    }
  }

  return (
    <>
      <button
        type="button"
        className={dash.apply}
        onClick={() => {
          setMade(null);
          setError(null);
          setPreset(PRESETS[0].id); // a fresh dialog: the safest preset, 365 days
          setNever(false);
          dialog.current?.querySelector("form")?.reset();
          dialog.current?.showModal();
        }}
      >
        Create key
      </button>
      <dialog ref={dialog} className={dash.dialog} aria-labelledby="create-key-title" onClose={() => setMade(null)}>
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (!busy) void submit(e.currentTarget);
          }}
        >
          <h2 id="create-key-title">Create an API key</h2>
          {made ? (
            <NewKeyPanel result={made} />
          ) : (
            <>
              <label className={dash.field}>
                <span>What the app does</span>
                <select value={preset} onChange={(e) => setPreset(e.target.value)}>
                  {PRESETS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
                <small className="mono">{scopes.join(", ")}</small>
              </label>
              {isAdmin && (
                <p className={dash.warn}>
                  ⚠ An admin key can read every chat, mint and revoke keys and delete documents. Give it only to a
                  trusted script, never to an app.
                </p>
              )}
              <label className={dash.field}>
                <span>App id</span>
                <input
                  name="app_id"
                  required
                  pattern="[a-z0-9\-]{2,64}"
                  title="Lowercase letters, digits and hyphens, 2 to 64 characters"
                  list="known-apps"
                  placeholder="e.g. hr-portal…"
                  autoComplete="off"
                  spellCheck={false}
                />
                <datalist id="known-apps">
                  {apps.map((a) => (
                    <option key={a} value={a} />
                  ))}
                </datalist>
              </label>
              {!isAdmin && <CollectionChecks collections={collections} checked={collections.slice(0, 1)} />}
              <div className={dash.field}>
                <span>Valid for</span>
                <div className={dash.inline}>
                  <input
                    name="days"
                    type="number"
                    min={1}
                    max={730}
                    defaultValue={365}
                    disabled={never}
                    required={!never}
                    aria-label="Days valid"
                  />
                  <span>days</span>
                  <label className={dash.check}>
                    <input type="checkbox" checked={never} onChange={(e) => setNever(e.target.checked)} />
                    <span>Never expires</span>
                  </label>
                </div>
              </div>
            </>
          )}
          {error && (
            <p role="alert" className={dash.error}>
              {error}
            </p>
          )}
          <div className={dash.dialogActions}>
            <button type="button" className={dash.secondary} onClick={() => dialog.current?.close()}>
              {made ? "Done" : "Cancel"}
            </button>
            {!made && (
              <button type="submit" className={dash.apply} disabled={busy} aria-busy={busy}>
                {busy ? "Creating…" : "Create key"}
              </button>
            )}
          </div>
        </form>
      </dialog>
    </>
  );
}

export function RotateKeyButton({ keyId, appId }: { keyId: string; appId: string }) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const toMessage = useErrorRedirect();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [made, setMade] = useState<Extract<NewKey, { ok: true }> | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    const r = await rotateKey(keyId);
    setBusy(false);
    if (r.ok) {
      // No refresh yet: the old key is now revoked, so a refresh would remove this row's buttons, this
      // dialog with them, and the new key before it can be copied. The page refreshes when the dialog closes.
      setMade(r);
      if (r.warning) toast("error", r.warning);
      else toast("ok", `Key rotated: ${keyId} revoked, ${r.keyId} created`);
    } else {
      setError(toMessage(r));
    }
  }

  return (
    <>
      <button
        type="button"
        className={dash.smallButton}
        onClick={() => {
          setMade(null);
          setError(null);
          dialog.current?.showModal();
        }}
      >
        Rotate
      </button>
      <dialog
        ref={dialog}
        className={dash.dialog}
        aria-label="Rotate key"
        onClose={() => {
          if (made) router.refresh(); // show the revoked key and the new one
          setMade(null);
        }}
      >
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (!busy && !made) void run();
          }}
        >
          <h2>Rotate this key?</h2>
          {made ? (
            <NewKeyPanel result={made} />
          ) : (
            <p>
              A new key for <span className="mono">{appId}</span> with the same permissions, collections and validity is
              made, and <span className="mono">{keyId}</span> stops working at once. Update the app&apos;s configuration
              with the new key right away.
            </p>
          )}
          {error && (
            <p role="alert" className={dash.error}>
              {error}
            </p>
          )}
          <div className={dash.dialogActions}>
            <button type="button" className={dash.secondary} onClick={() => dialog.current?.close()}>
              {made ? "Done" : "Cancel"}
            </button>
            {!made && (
              <button type="submit" className={dash.danger} disabled={busy} aria-busy={busy}>
                {busy ? "Rotating…" : "Rotate key"}
              </button>
            )}
          </div>
        </form>
      </dialog>
    </>
  );
}

export function EditKeyButton({
  keyId,
  collections,
  current,
  expiresLabel,
}: {
  keyId: string;
  collections: string[];
  current: string[];
  expiresLabel: string;
}) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const toMessage = useErrorRedirect();
  const [expiry, setExpiry] = useState<"keep" | "days" | "never">("keep");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(form: HTMLFormElement) {
    const data = new FormData(form);
    setBusy(true);
    setError(null);
    const r = await editKey(
      keyId,
      data.getAll("collections").map(String),
      expiry === "keep"
        ? { change: false }
        : { change: true, validDays: expiry === "never" ? null : Number(data.get("days")) },
    );
    setBusy(false);
    if (r.ok) {
      dialog.current?.close();
      toast("ok", `Key ${keyId} updated`);
      router.refresh();
    } else {
      setError(toMessage(r));
    }
  }

  return (
    <>
      <button
        type="button"
        className={dash.smallButton}
        onClick={() => {
          setExpiry("keep");
          setError(null);
          dialog.current?.showModal();
        }}
      >
        Edit
      </button>
      <dialog ref={dialog} className={dash.dialog} aria-label="Edit key">
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (!busy) void submit(e.currentTarget);
          }}
        >
          <h2>
            Edit key <span className="mono">{keyId}</span>
          </h2>
          <CollectionChecks collections={collections} checked={current} />
          <label className={dash.field}>
            <span>Expiry</span>
            <select value={expiry} onChange={(e) => setExpiry(e.target.value as typeof expiry)}>
              <option value="keep">Keep ({expiresLabel})</option>
              <option value="days">Valid for a number of days from today</option>
              <option value="never">Never expires</option>
            </select>
          </label>
          {expiry === "days" && (
            <label className={dash.field}>
              <span>Days from today</span>
              <input name="days" type="number" min={1} max={730} defaultValue={365} required />
            </label>
          )}
          <small className={dash.muted}>Permissions can&apos;t be edited: rotate the key, or create a new one.</small>
          {error && (
            <p role="alert" className={dash.error}>
              {error}
            </p>
          )}
          <div className={dash.dialogActions}>
            <button type="button" className={dash.secondary} onClick={() => dialog.current?.close()}>
              Cancel
            </button>
            <button type="submit" className={dash.apply} disabled={busy} aria-busy={busy}>
              {busy ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}

const PROFILE_FIELDS: { name: keyof Profile; label: string; long?: boolean; type?: string }[] = [
  { name: "display_name", label: "Name" },
  { name: "description", label: "What it is", long: true },
  { name: "company", label: "Company or department" },
  { name: "owner_name", label: "Owner" },
  { name: "owner_email", label: "Owner's email", type: "email" },
  { name: "notes", label: "Notes", long: true },
];

export function EditProfileButton({ appId, profile }: { appId: string; profile: Profile }) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const toMessage = useErrorRedirect();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(form: HTMLFormElement) {
    const data = new FormData(form);
    const value = (n: string) => String(data.get(n) ?? "").trim() || null; // empty field = cleared
    setBusy(true);
    setError(null);
    const r = await saveProfile(
      appId,
      Object.fromEntries(PROFILE_FIELDS.map((f) => [f.name, value(f.name)])) as Profile,
    );
    setBusy(false);
    if (r.ok) {
      dialog.current?.close();
      toast("ok", `Profile of ${appId} saved`);
      router.refresh();
    } else {
      setError(toMessage(r));
    }
  }

  return (
    <>
      <button
        type="button"
        className={dash.smallButton}
        onClick={() => {
          setError(null);
          dialog.current?.showModal();
        }}
      >
        Edit profile
      </button>
      <dialog ref={dialog} className={dash.dialog} aria-label="Edit app profile">
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (!busy) void submit(e.currentTarget);
          }}
        >
          <h2>
            Profile of <span className="mono">{appId}</span>
          </h2>
          {PROFILE_FIELDS.map((f) => (
            <label key={f.name} className={dash.field}>
              <span>{f.label}</span>
              {f.long ? (
                <textarea
                  name={f.name}
                  defaultValue={profile[f.name] ?? ""}
                  rows={2}
                  maxLength={f.name === "notes" ? 2000 : 500}
                />
              ) : (
                <input
                  name={f.name}
                  type={f.type ?? "text"}
                  defaultValue={profile[f.name] ?? ""}
                  maxLength={f.name === "owner_email" ? 200 : 100}
                />
              )}
            </label>
          ))}
          <small className={dash.muted}>Notes only: nothing here changes what the app may do (its keys decide).</small>
          {error && (
            <p role="alert" className={dash.error}>
              {error}
            </p>
          )}
          <div className={dash.dialogActions}>
            <button type="button" className={dash.secondary} onClick={() => dialog.current?.close()}>
              Cancel
            </button>
            <button type="submit" className={dash.apply} disabled={busy} aria-busy={busy}>
              {busy ? "Saving…" : "Save profile"}
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}

/** Disconnect an app: all keys revoked, profile removed; optionally every chat of its users erased.
 *  The app id must be typed to confirm, as for deleting one user's chats. */
export function DisconnectAppButton({
  appId,
  users,
  activeKeys,
  hasAdminKey,
}: {
  appId: string;
  users: number;
  activeKeys: number;
  hasAdminKey: boolean; // an active admin key: scripts using it stop too
}) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const toMessage = useErrorRedirect();
  const [typed, setTyped] = useState("");
  const [erase, setErase] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const matches = typed.trim() === appId;

  async function run() {
    setBusy(true);
    setError(null);
    const r = await disconnectApp(appId, erase);
    setBusy(false);
    if (!r.ok) return setError(toMessage(r));
    const d = r.data;
    const parts = [`${d.keys_revoked} ${d.keys_revoked === 1 ? "key" : "keys"} revoked`];
    if (d.profile_removed) parts.push("profile removed");
    if (erase) parts.push(`${d.conversations} conversations and ${d.messages} messages erased`);
    toast("ok", `${appId} disconnected: ${parts.join(", ")}`);
    dialog.current?.close();
    router.refresh();
  }

  return (
    <>
      <button
        type="button"
        className={dash.dangerSmall}
        onClick={() => {
          setTyped("");
          setErase(false);
          setError(null);
          dialog.current?.showModal();
        }}
      >
        Disconnect app…
      </button>
      <dialog ref={dialog} className={dash.dialog} aria-labelledby={`disconnect-${appId}`}>
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (matches && !busy) void run();
          }}
        >
          <h2 id={`disconnect-${appId}`}>
            Disconnect <span className="mono">{appId}</span>?
          </h2>
          <p>
            {activeKeys > 0
              ? `Its ${activeKeys} active ${activeKeys === 1 ? "key stops" : "keys stop"} working at once`
              : "It has no active keys left"}{" "}
            and its profile is removed. Its revoked keys, request log and (unless erased below) its users&apos; chats
            stay as history; it moves to &quot;Disconnected apps&quot;.
          </p>
          {hasAdminKey && (
            <p className={dash.error}>
              ⚠ This app holds an active <strong>admin</strong> key: every script using it stops working. Make sure
              another admin key or a super admin account remains.
            </p>
          )}
          <label className={dash.check}>
            <input type="checkbox" checked={erase} onChange={(e) => setErase(e.target.checked)} disabled={busy} />
            <span>
              Also erase all chats of its {users} {users === 1 ? "user" : "users"} (can&apos;t be undone)
            </span>
          </label>
          <label className={dash.field}>
            <span>
              Type <span className="mono">{appId}</span> to confirm
            </span>
            <input
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              autoComplete="off"
              spellCheck={false}
              disabled={busy}
            />
          </label>
          {error && (
            <p role="alert" className={dash.error}>
              {error}
            </p>
          )}
          <div className={dash.dialogActions}>
            <button type="button" className={dash.secondary} onClick={() => dialog.current?.close()}>
              Cancel
            </button>
            <button type="submit" className={dash.danger} disabled={!matches || busy} aria-busy={busy}>
              {busy ? "Disconnecting…" : erase ? "Disconnect and erase chats" : "Disconnect app"}
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}

/** Remove permanently: for a disconnected app with no chats left. Its revoked key rows (and any profile) are
 *  deleted, so it leaves the list. The app id must be typed to confirm. */
export function RemoveAppButton({ appId, keys }: { appId: string; keys: number }) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const toMessage = useErrorRedirect();
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const matches = typed.trim() === appId;

  async function run() {
    setBusy(true);
    setError(null);
    const r = await removeApp(appId);
    setBusy(false);
    if (!r.ok) return setError(toMessage(r));
    toast(
      "ok",
      `${appId} removed permanently (${r.data.keys_removed} revoked ${r.data.keys_removed === 1 ? "key" : "keys"})`,
    );
    dialog.current?.close();
    router.refresh();
  }

  return (
    <>
      <button
        type="button"
        className={dash.dangerSmall}
        onClick={() => {
          setTyped("");
          setError(null);
          dialog.current?.showModal();
        }}
      >
        Remove permanently…
      </button>
      <dialog ref={dialog} className={dash.dialog} aria-labelledby={`remove-${appId}`}>
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (matches && !busy) void run();
          }}
        >
          <h2 id={`remove-${appId}`}>
            Remove <span className="mono">{appId}</span> permanently?
          </h2>
          <p>
            Its {keys} revoked {keys === 1 ? "key is" : "keys are"} deleted and the app leaves this list. The record of
            which keys it had is gone for good; its request-log rows stay until the 90-day clean-up. This can&apos;t be
            undone.
          </p>
          <label className={dash.field}>
            <span>
              Type <span className="mono">{appId}</span> to confirm
            </span>
            <input
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              autoComplete="off"
              spellCheck={false}
              disabled={busy}
            />
          </label>
          {error && (
            <p role="alert" className={dash.error}>
              {error}
            </p>
          )}
          <div className={dash.dialogActions}>
            <button type="button" className={dash.secondary} onClick={() => dialog.current?.close()}>
              Cancel
            </button>
            <button type="submit" className={dash.danger} disabled={!matches || busy} aria-busy={busy}>
              {busy ? "Removing…" : "Remove permanently"}
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}
