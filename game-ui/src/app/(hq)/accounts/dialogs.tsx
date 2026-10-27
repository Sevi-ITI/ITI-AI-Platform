"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import dash from "../kit/dashboard.module.css";
import FormDialog from "../kit/form-dialog";
import { toast } from "../kit/toast";
import { addAccount, deleteAccount, resetPassword, updateAccount } from "./actions";

// The Accounts page's form dialogs: add an account, edit name / role, reset a password, delete a deactivated one.
// Passwords are read from the form once and sent to the server action; they are never kept in state.

type Role = "super_admin" | "supervisor" | "tester";

// The role, and for a tester the collections they may ask (at least one; FastAPI checks it too).
function RoleFields({ value, collections, checked = [] }: { value?: Role; collections: string[]; checked?: string[] }) {
  const [role, setRole] = useState<Role>(value ?? "supervisor");
  return (
    <>
      <label className={dash.field}>
        <span>Role</span>
        <select name="role" value={role} onChange={(e) => setRole(e.target.value as Role)}>
          <option value="supervisor">Supervisor: reads everything, chats, uploads new documents</option>
          <option value="tester">Tester: only the Chat page, asks the collections below, sees only own chats</option>
          <option value="super_admin">Super admin: everything, including keys and accounts</option>
        </select>
      </label>
      {role === "tester" && (
        <fieldset className={dash.checks}>
          <legend>Collections this tester may ask</legend>
          {collections.length === 0 && <span className={dash.muted}>No collections yet: create one on Documents.</span>}
          {collections.map((name) => (
            <label key={name} className={dash.check}>
              <input type="checkbox" name="collections" value={name} defaultChecked={checked.includes(name)} />
              <span className="mono" translate="no">
                {name}
              </span>
            </label>
          ))}
        </fieldset>
      )}
    </>
  );
}

/** For a tester: the ticked collections (sent), else nothing (other roles may ask every collection). */
const collectionsOf = (data: FormData) =>
  data.get("role") === "tester" ? { collections: data.getAll("collections").map(String) } : {};

function PasswordFields() {
  return (
    <>
      <label className={dash.field}>
        <span>Password (at least 12 characters)</span>
        <input name="password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" />
      </label>
      <label className={dash.field}>
        <span>Type it again</span>
        <input name="again" type="password" required minLength={12} maxLength={128} autoComplete="new-password" />
      </label>
    </>
  );
}

const passwordOf = (data: FormData) => {
  const password = String(data.get("password") ?? "");
  return password === String(data.get("again") ?? "") ? password : null;
};

export function AddAccountButton({ collections }: { collections: string[] }) {
  return (
    <FormDialog
      button="Add account"
      buttonClass={dash.apply}
      title="Add a console account"
      submitLabel="Add account"
      done={(data) => `Account ${String(data.get("username") ?? "").trim()} added`}
      onSubmit={(data) => {
        const password = passwordOf(data);
        if (password === null) return Promise.resolve("The two passwords don't match.");
        return addAccount({
          username: String(data.get("username") ?? "").trim(),
          display_name: String(data.get("display_name") ?? "").trim() || null,
          role: data.get("role") as Role,
          password,
          ...collectionsOf(data),
        });
      }}
    >
      <label className={dash.field}>
        <span>Username (used to log in)</span>
        <input
          name="username"
          required
          pattern="[a-z][a-z0-9._\-]{2,31}"
          title="Lowercase, 3 to 32 characters: letters, digits, dot, dash, underscore; starts with a letter"
          placeholder="e.g. j.santos…"
          autoComplete="off"
          spellCheck={false}
        />
      </label>
      <label className={dash.field}>
        <span>Name shown in the console</span>
        <input name="display_name" maxLength={100} placeholder="e.g. Juan Santos…" autoComplete="off" />
      </label>
      <RoleFields collections={collections} />
      <PasswordFields />
      <small className={dash.muted}>Give the password to the person directly (not by chat or email).</small>
    </FormDialog>
  );
}

export function EditAccountButton({
  username,
  displayName,
  role,
  collections,
  checked,
}: {
  username: string;
  displayName: string | null;
  role: Role;
  collections: string[];
  checked: string[];
}) {
  return (
    <FormDialog
      button="Edit"
      buttonClass={dash.smallButton}
      title={`Edit ${username}`}
      submitLabel="Save"
      done={() => `${username} saved`}
      onSubmit={(data) =>
        updateAccount(username, {
          display_name: String(data.get("display_name") ?? "").trim() || null,
          role: data.get("role") as Role,
          ...collectionsOf(data),
        })
      }
    >
      <label className={dash.field}>
        <span>Name shown in the console</span>
        <input name="display_name" maxLength={100} defaultValue={displayName ?? ""} autoComplete="off" />
      </label>
      <RoleFields value={role} collections={collections} checked={checked} />
      <small className={dash.muted}>A role change applies from the person&apos;s next page load.</small>
    </FormDialog>
  );
}

export function ResetPasswordButton({ username }: { username: string }) {
  return (
    <FormDialog
      button="Reset password"
      buttonClass={dash.smallButton}
      title={`New password for ${username}`}
      submitLabel="Set password"
      done={() => `New password set for ${username}; they were logged out`}
      onSubmit={(data) => {
        const password = passwordOf(data);
        return password === null
          ? Promise.resolve("The two passwords don't match.")
          : resetPassword(username, password);
      }}
    >
      <PasswordFields />
      <small className={dash.muted}>
        It also unlocks the account and logs {username} out everywhere. Give the new password to them directly.
      </small>
    </FormDialog>
  );
}

/** Delete a deactivated account for good (UI-R2g). The username must be typed to confirm, as for removing an app.
 *  Only deactivated rows get this button; FastAPI refuses an active account too (409). */
export function DeleteAccountButton({ username }: { username: string }) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const matches = typed.trim() === username;

  async function run() {
    setBusy(true);
    setError(null);
    const r = await deleteAccount(username);
    setBusy(false);
    if (!r.ok) {
      if (r.status === 401) return router.push("/login"); // the session is over
      return setError(r.message);
    }
    toast("ok", `${username} deleted`);
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
        Delete…
      </button>
      <dialog ref={dialog} className={dash.dialog} aria-labelledby={`delete-${username}`}>
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (matches && !busy) void run();
          }}
        >
          <h2 id={`delete-${username}`}>
            Delete <span className="mono">{username}</span>?
          </h2>
          <p>
            The account is removed for good: it leaves this list and can never log in again. Their chats stay; a new
            account with the same username would see them in Users &amp; chats. This can&apos;t be undone.
          </p>
          <label className={dash.field}>
            <span>
              Type <span className="mono">{username}</span> to confirm
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
              {busy ? "Deleting…" : "Delete account"}
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}
