"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { PlusIcon } from "../icons";
import { createCollection, jobStatus } from "./actions";
import dash from "../dashboard.module.css";
import { toast } from "../toast";
import styles from "./chat.module.css";

// The + button (or a text button, with `label`) and its dialog: upload a PDF into a collection, or into a new
// collection made here. The file goes to /api/documents (streamed to FastAPI); then the indexing job is checked
// until it ends. With `canReplace` (super admin), a name that already exists can be replaced: same file, sent
// again with replace=true (FastAPI refuses supervisors anyway).

const NEW = "__new__";
const GLOBAL = "__global__";

// POST the form to /api/documents with upload progress (fetch can't report it; XMLHttpRequest can).
type UploadReply = { job_id?: string; error?: { code?: string; message?: string } } | null;

function send(body: FormData, onProgress: (part: number) => void): Promise<{ status: number; json: UploadReply }> {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/documents");
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onload = () => {
      let json: UploadReply = null;
      try {
        json = JSON.parse(xhr.responseText);
      } catch {}
      resolve({ status: xhr.status, json });
    };
    xhr.onerror = () => resolve({ status: 0, json: null });
    xhr.send(body);
  });
}
type State =
  | { step: "idle" }
  | { step: "working"; label: string; progress: number | null } // 0–1 while uploading; null = indexing
  | { step: "done"; label: string }
  | { step: "error"; label: string }
  | { step: "exists"; label: string };

export default function AddDocument({
  collections,
  initial,
  label,
  canReplace = false,
  companies,
}: {
  collections: string[];
  initial?: string;
  label?: string;
  canReplace?: boolean;
  companies?: { company_id: string; name: string }[]; // given: a new collection asks whose it is (else ITI's)
}) {
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

  async function upload(form: HTMLFormElement, replace: boolean) {
    const data = new FormData(form);
    const file = data.get("file");
    if (!(file instanceof File) || file.size === 0) return setState({ step: "error", label: "Choose a PDF." });

    let collection = choice;
    if (choice === NEW) {
      setState({ step: "working", label: "Creating the collection…", progress: null });
      const owner = String(data.get("company") ?? "iti");
      const made = await createCollection(String(data.get("name") ?? "").trim(), owner === GLOBAL ? null : owner);
      if (!made.ok) return setState({ step: "error", label: made.message });
      collection = made.data.name;
      toast("ok", `Collection ${collection} created`);
      setCreated((c) => [...c, collection]);
      setChoice(collection); // a retry uploads into it instead of creating it again
      router.refresh();
    }

    const fail = (label: string) => {
      setState({ step: "error", label });
      toast("error", `Upload of ${file.name} failed: ${label}`);
    };
    setState({ step: "working", label: `Uploading ${file.name}…`, progress: 0 });
    const body = new FormData();
    body.set("collection", collection);
    body.set("file", file);
    if (replace) body.set("replace", "true");
    const res = await send(body, (part) =>
      setState({ step: "working", label: `Uploading ${file.name}…`, progress: part }),
    );
    if (res.status === 401) return router.push("/login");
    const json = res.json;
    if (res.status < 200 || res.status >= 300) {
      if (json?.error?.code === "document_exists" && canReplace) {
        return setState({
          step: "exists",
          label: `${file.name} is already in ${collection}. Replace the existing file?`,
        });
      }
      return fail(json?.error?.message ?? "the service is not reachable. Check that FastAPI is running.");
    }

    setState({
      step: "working",
      label: `Indexing ${file.name}: reading the pages and building the search index…`,
      progress: null,
    });
    for (;;) {
      await new Promise((r) => setTimeout(r, 1500));
      const job = await jobStatus(json?.job_id ?? "");
      if (!job.ok) return fail(job.message);
      if (job.data.status === "failed") return fail(job.data.error ?? "indexing failed.");
      if (job.data.status === "done") {
        form.reset();
        const label = `${file.name} is ready in ${collection}: ${job.data.chunks ?? 0} passages indexed.`;
        setState({ step: "done", label });
        toast("ok", label);
        router.refresh(); // document counts in the picker
        return;
      }
    }
  }

  return (
    <>
      {label ? (
        <button type="button" className={dash.apply} onClick={open}>
          {label}
        </button>
      ) : (
        <button
          type="button"
          className={styles.roundGhost}
          onClick={open}
          aria-label="Add a document"
          title="Add a document"
        >
          <PlusIcon />
        </button>
      )}
      <dialog ref={dialog} className={dash.dialog} aria-labelledby="add-document-title">
        <form
          className={dash.dialogForm}
          onSubmit={(e) => {
            e.preventDefault();
            void upload(e.currentTarget, state.step === "exists");
          }}
          // a different file or collection is a new question: back to a plain upload
          onChange={() => state.step === "exists" && setState({ step: "idle" })}
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
          {choice === NEW && companies && (
            <label className={dash.field}>
              <span>For company</span>
              <select name="company" defaultValue="iti" disabled={busy}>
                {companies.map((c) => (
                  <option key={c.company_id} value={c.company_id}>
                    {c.name} ({c.company_id})
                  </option>
                ))}
                <option value={GLOBAL}>Global: every company may be given it</option>
              </select>
              <small className={styles.muted}>
                Only that company&apos;s keys can be given it (Global: any company&apos;s).
              </small>
            </label>
          )}
          <p
            role="status"
            className={
              state.step === "error"
                ? styles.failed
                : state.step === "done"
                  ? styles.ready
                  : state.step === "exists"
                    ? dash.warn
                    : styles.muted
            }
          >
            {state.step === "idle" ? "Only PDFs with a text layer can be read (no scanned images)." : state.label}
          </p>
          {state.step === "working" && (
            // a real percentage while the file uploads; a moving bar while it is indexed (no percentage exists)
            <div
              className={state.progress === null ? `${dash.progress} ${dash.progressBusy}` : dash.progress}
              role="progressbar"
              aria-label={state.label}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={state.progress === null ? undefined : Math.round(state.progress * 100)}
            >
              <span style={state.progress === null ? undefined : { width: `${Math.round(state.progress * 100)}%` }} />
            </div>
          )}
          <div className={dash.dialogActions}>
            <button type="button" className={styles.secondary} onClick={() => dialog.current?.close()}>
              {state.step === "done" ? "Close" : "Cancel"}
            </button>
            <button type="submit" className={styles.send} disabled={busy} aria-busy={busy}>
              {busy ? "Working…" : state.step === "exists" ? "Replace file" : "Upload"}
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}
