"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import type { ConfirmResult } from "../confirm-action";
import dash from "../dashboard.module.css";
import { toast } from "../toast";
import { addAccount, resetPassword, updateAccount } from "./actions";

// The Accounts page's form dialogs: add an account, edit name / role, reset a password. Passwords are read from
// the form once and sent to the server action; they are never kept in state.

type Role = "super_admin" | "supervisor";

function FormDialog({
  button,
  buttonClass,
  title,
  submitLabel,
  children,
  onSubmit,
  done,
}: {
  button: string;
  buttonClass: string;
  title: string;
  submitLabel: string;
  children: React.ReactNode;
  onSubmit: (data: FormData) => Promise<ConfirmResult | string>; // a string = the form's own complaint
  done: (data: FormData) => string; // the toast after it worked
}) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(form: HTMLFormElement) {
    setBusy(true);
    setError(null);
    const data = new FormData(form);
    const r = await onSubmit(data);
    setBusy(false);
    if (typeof r === "string") return setError(r);
    if (r.ok) {
      toast("ok", done(data));
      form.reset();
      dialog.current?.close();
      router.refresh();
    } else if (r.status === 401) {
      router.push("/login");
    } else {
      setError(r.message);
    }
  }

  return (
    <>
      <button
        type="button"
        className={buttonClass}
        onClick={() => {
          setError(null);
          dialog.current?.querySelector("form")?.reset();
          dialog.current?.showModal();
        }}
      >
        {button}
      </button>
      <dialog ref={dialog} className={dash.dialog} aria-label={title}>
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (!busy) void submit(e.currentTarget);
          }}
        >
          <h2>{title}</h2>
          {children}
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
              {busy ? "Saving…" : submitLabel}
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}

function RoleSelect({ value }: { value?: Role }) {
  return (
    <label className={dash.field}>
      <span>Role</span>
      <select name="role" defaultValue={value ?? "supervisor"}>
        <option value="supervisor">Supervisor: reads everything, chats, uploads new documents</option>
        <option value="super_admin">Super admin: everything, including keys and accounts</option>
      </select>
    </label>
  );
}

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

export function AddAccountButton() {
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
      <RoleSelect />
      <PasswordFields />
      <small className={dash.muted}>Give the password to the person directly (not by chat or email).</small>
    </FormDialog>
  );
}

export function EditAccountButton({
  username,
  displayName,
  role,
}: {
  username: string;
  displayName: string | null;
  role: Role;
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
        })
      }
    >
      <label className={dash.field}>
        <span>Name shown in the console</span>
        <input name="display_name" maxLength={100} defaultValue={displayName ?? ""} autoComplete="off" />
      </label>
      <RoleSelect value={role} />
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
