"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { PlusIcon } from "../icons";
import { createCollection, jobStatus } from "./actions";
import dash from "../dashboard.module.css";
import styles from "./chat.module.css";

// The + button and its dialog: upload a PDF into a collection, or into a new collection made here.
// The file goes to /api/documents (streamed to FastAPI); then the indexing job is checked until it ends.

const NEW = "__new__";
type State =
  | { step: "idle" }
  | { step: "working"; label: string }
  | { step: "done"; label: string }
  | { step: "error"; label: string };

export default function AddDocument({ collections, initial }: { collections: string[]; initial?: string }) {
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const [created, setCreated] = useState<string[]>([]); // made here, until the page shows them
  const [choice, setChoice] = useState(initial ?? collections[0] ?? NEW);
  const [state, setState] = useState<State>({ step: "idle" });
  const options = [...collections, ...created.filter((c) => !collections.includes(c))];
  const busy = state.step === "working";

  function open() {
    if (!busy) {
      setState({ step: "idle" });
      if (initial) setChoice(initial); // start on the collection the question box uses
    }
    dialog.current?.showModal();
  }

  async function upload(form: HTMLFormElement) {
    const data = new FormData(form);
    const file = data.get("file");
    if (!(file instanceof File) || file.size === 0) return setState({ step: "error", label: "Choose a PDF." });

    let collection = choice;
    if (choice === NEW) {
      setState({ step: "working", label: "Creating the collection…" });
      const made = await createCollection(String(data.get("name") ?? "").trim());
      if (!made.ok) return setState({ step: "error", label: made.message });
      collection = made.data.name;
      setCreated((c) => [...c, collection]);
      setChoice(collection); // a retry uploads into it instead of creating it again
      router.refresh();
    }

    setState({ step: "working", label: `Uploading ${file.name}…` });
    const body = new FormData();
    body.set("collection", collection);
    body.set("file", file);
    const res = await fetch("/api/documents", { method: "POST", body }).catch(() => null);
    if (res?.status === 401) return router.push("/login");
    const json = await res?.json().catch(() => null);
    if (!res?.ok) {
      return setState({
        step: "error",
        label: json?.error?.message ?? "The upload failed. Check that FastAPI is running.",
      });
    }

    setState({
      step: "working",
      label: `Indexing ${file.name}: reading the pages and building the search index…`,
    });
    for (;;) {
      await new Promise((r) => setTimeout(r, 1500));
      const job = await jobStatus(json.job_id);
      if (!job.ok) return setState({ step: "error", label: job.message });
      if (job.data.status === "failed")
        return setState({
          step: "error",
          label: job.data.error ?? "Indexing failed.",
        });
      if (job.data.status === "done") {
        form.reset();
        setState({
          step: "done",
          label: `${file.name} is ready in ${collection}: ${job.data.chunks ?? 0} passages indexed.`,
        });
        router.refresh(); // document counts in the picker
        return;
      }
    }
  }

  return (
    <>
      <button
        type="button"
        className={styles.roundGhost}
        onClick={open}
        aria-label="Add a document"
        title="Add a document"
      >
        <PlusIcon />
      </button>
      <dialog ref={dialog} className={dash.dialog} aria-labelledby="add-document-title">
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void upload(e.currentTarget);
          }}
        >
          <h2 id="add-document-title">Add a document</h2>
          <label className={dash.field}>
            <span>PDF file</span>
            <input type="file" name="file" accept="application/pdf,.pdf" required disabled={busy} />
          </label>
          <label className={dash.field}>
            <span>Collection</span>
            <select value={choice} onChange={(e) => setChoice(e.target.value)} disabled={busy}>
              {options.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
              <option value={NEW}>+ New collection…</option>
            </select>
          </label>
          {choice === NEW && (
            <label className={dash.field}>
              <span>New collection name</span>
              <input
                name="name"
                required
                pattern="[a-z0-9][a-z0-9\-]{1,63}"
                title="Lowercase letters, digits and hyphens, 2 to 64 characters"
                placeholder="e.g. finance-docs…"
                autoComplete="off"
                spellCheck={false}
                disabled={busy}
              />
              <small className={styles.muted}>
                Lowercase letters, digits and hyphens. API keys get it only when you add it to them.
              </small>
            </label>
          )}
          <p
            role="status"
            className={state.step === "error" ? styles.failed : state.step === "done" ? styles.ready : styles.muted}
          >
            {state.step === "idle" ? "Only PDFs with a text layer can be read (no scanned images)." : state.label}
          </p>
          <div className={dash.dialogActions}>
            <button type="button" className={styles.secondary} onClick={() => dialog.current?.close()}>
              {state.step === "done" ? "Close" : "Cancel"}
            </button>
            <button type="submit" className={styles.send} disabled={busy} aria-busy={busy}>
              {busy ? "Working…" : "Upload"}
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}
