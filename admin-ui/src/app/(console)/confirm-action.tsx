"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import dash from "./dashboard.module.css";
import { toast } from "./toast";

// A red button that asks before it acts: delete a document, revoke a key, deactivate an account.
// `quiet` makes both buttons neutral, for an undoable change (reactivate an account).
// `action` is a server action already bound to its arguments (e.g. deleteDocument.bind(null, collection, name));
// it returns FastAPI's message on failure. On success the page refreshes.

export type ConfirmResult = { ok: true } | { ok: false; message: string; status: number };

export default function ConfirmAction({
  label,
  title,
  children,
  confirmLabel,
  action,
  quiet = false,
  done,
}: {
  label: string;
  title: string;
  children: React.ReactNode;
  confirmLabel: string;
  action: () => Promise<ConfirmResult>;
  quiet?: boolean;
  done: string; // the toast after it worked, e.g. "Key 3f2a… revoked"
}) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    const r = await action();
    setBusy(false);
    if (r.ok) {
      dialog.current?.close();
      toast("ok", done);
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
        className={quiet ? dash.smallButton : dash.dangerSmall}
        onClick={() => {
          setError(null);
          dialog.current?.showModal();
        }}
      >
        {label}
      </button>
      <dialog ref={dialog} className={dash.dialog} aria-label={title}>
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (!busy) void run();
          }}
        >
          <h2>{title}</h2>
          <div>{children}</div>
          {error && (
            <p role="alert" className={dash.error}>
              {error}
            </p>
          )}
          <div className={dash.dialogActions}>
            <button type="button" className={dash.secondary} onClick={() => dialog.current?.close()}>
              Cancel
            </button>
            <button type="submit" className={quiet ? dash.apply : dash.danger} disabled={busy} aria-busy={busy}>
              {busy ? "Working…" : confirmLabel}
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}
