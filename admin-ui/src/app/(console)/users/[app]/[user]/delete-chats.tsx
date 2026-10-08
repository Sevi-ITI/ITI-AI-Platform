"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import dash from "../../../dashboard.module.css";
import { deleteUserChats } from "../../actions";

// "Delete this user's chats": a dialog that only deletes once the user id is typed exactly.
// Shows what was removed (keep it as the record of the erasure request).

type State = { step: "idle" | "working" } | { step: "done" | "error"; label: string };

export default function DeleteChats({ appId, userId }: { appId: string; userId: string }) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const [typed, setTyped] = useState("");
  const [state, setState] = useState<State>({ step: "idle" });
  const matches = typed.trim() === userId;
  const busy = state.step === "working";

  async function erase() {
    setState({ step: "working" });
    const r = await deleteUserChats(appId, userId);
    if (!r.ok) {
      if (r.status === 401) return router.push("/login");
      return setState({ step: "error", label: r.message });
    }
    const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
    setState({
      step: "done",
      label: `Deleted ${plural(r.data.conversations, "conversation")} and ${plural(r.data.messages, "message")} of ${userId} in ${appId}.`,
    });
    router.refresh();
  }

  return (
    <>
      <button
        type="button"
        className={dash.danger}
        onClick={() => {
          setTyped("");
          setState({ step: "idle" });
          dialog.current?.showModal();
        }}
      >
        Delete this user&apos;s chats…
      </button>
      <dialog ref={dialog} className={dash.dialog} aria-labelledby="delete-chats-title">
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            if (matches && !busy) void erase();
          }}
        >
          <h2 id="delete-chats-title">Delete this user&apos;s chats?</h2>
          <p>
            Every conversation and message of{" "}
            <strong className={`mono ${dash.nowrap}`} translate="no">
              {userId}
            </strong>{" "}
            in{" "}
            <strong className={`mono ${dash.nowrap}`} translate="no">
              {appId}
            </strong>{" "}
            is erased for good. Their request-log rows (no chat text) stay until the 90-day clean-up.
          </p>
          {state.step === "done" ? (
            <p role="status" className={dash.ok}>
              ✓ {state.label}
            </p>
          ) : (
            <label className={dash.field}>
              <span>
                Type <span className="mono">{userId}</span> to confirm
              </span>
              <input
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                autoComplete="off"
                spellCheck={false}
                disabled={busy}
              />
            </label>
          )}
          {state.step === "error" && (
            <p role="alert" className={dash.error}>
              {state.label}
            </p>
          )}
          <div className={dash.dialogActions}>
            <button type="button" className={dash.secondary} onClick={() => dialog.current?.close()}>
              {state.step === "done" ? "Close" : "Cancel"}
            </button>
            {state.step !== "done" && (
              <button type="submit" className={dash.danger} disabled={!matches || busy} aria-busy={busy}>
                {busy ? "Deleting…" : "Delete chats"}
              </button>
            )}
          </div>
        </form>
      </dialog>
    </>
  );
}
