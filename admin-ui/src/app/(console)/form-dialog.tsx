"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import type { ConfirmResult } from "./confirm-action";
import dash from "./dashboard.module.css";
import { LockIcon } from "./icons";
import { toast } from "./toast";

// 8.6e-3: what a locked button says on hover (the gate bar at the top of the page explains it too)
export const LOCKED_HINT = "Locked: unlock with your security password first (the bar at the top of this page).";

// A button that opens a small form in a dialog (add an account, add a company, edit a name...). onSubmit gets the
// form's data and returns the server action's result, or a string for the form's own complaint; `done` is the
// toast after it worked. Used by Accounts and Companies. `locked` (8.6e-3): the button is greyed out with a padlock
// until the security password is unlocked (FastAPI refuses the change anyway).

export default function FormDialog({
  button,
  buttonClass,
  title,
  submitLabel,
  children,
  onSubmit,
  done,
  locked = false,
}: {
  button: string;
  buttonClass: string;
  title: string;
  submitLabel: string;
  children: React.ReactNode;
  onSubmit: (data: FormData) => Promise<ConfirmResult | string>; // a string = the form's own complaint
  done: (data: FormData) => string; // the toast after it worked
  locked?: boolean;
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
        className={locked ? `${buttonClass} ${dash.lockedButton}` : buttonClass}
        disabled={locked}
        title={locked ? LOCKED_HINT : undefined}
        onClick={() => {
          setError(null);
          dialog.current?.querySelector("form")?.reset();
          dialog.current?.showModal();
        }}
      >
        {locked && <LockIcon />}
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
