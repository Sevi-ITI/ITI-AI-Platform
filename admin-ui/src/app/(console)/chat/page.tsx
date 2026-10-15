import { displayMessage } from "@/lib/api/api-error";
import { callApi, endSessionOn401 } from "@/lib/api/client";

import { Problem } from "../widgets";
import styles from "./chat.module.css";
import Composer from "./composer";
import { chatCollections } from "./data";

export const metadata = { title: "Chat" };

// How many suggestion chips show above the question box (Vince: three at most)
const SUGGESTIONS = 3;

/** "ITI_Code-of_Discipline.pdf" → "ITI Code of Discipline": underscores and dashes become spaces, and a name
 * written as one word gets spaces where the case or digits change ("LaborCodePH2017" → "Labor Code PH 2017"). */
function titleOf(filename: string): string {
  return filename
    .replace(/\.[a-z0-9]+$/i, "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/([A-Za-z])(\d)/g, "$1 $2")
    .replace(/[_\s-]+/g, " ")
    .trim();
}

// A new conversation: choose the collection (it stays fixed for the conversation), then ask.
export default async function NewChatPage() {
  const [collections, documents] = await Promise.all([
    chatCollections(),
    // the newest files of every collection, for the suggestion chips (no chips if this fails: they are a help only)
    callApi((api) => api.GET("/v1/admin/documents", { params: { query: { limit: 100 } } })),
  ]);
  endSessionOn401(collections, documents);

  // Per collection: up to three questions about its newest indexed files, so a suggestion always fits the
  // collection that is picked (one question per file; a file uploaded twice counts once).
  const suggestions: Record<string, string[]> = {};
  for (const d of documents.ok ? documents.data : []) {
    if (d.job_status !== "done") continue;
    const list = (suggestions[d.collection] ??= []);
    const question = `What does ${titleOf(d.filename)} cover?`;
    if (list.length < SUGGESTIONS && !list.includes(question)) list.push(question);
  }

  return (
    <section className={styles.thread} aria-label="New chat">
      {/* what this is (left) and how to get a good answer (right); stacked on narrow screens */}
      <div className={styles.empty}>
        <div className={styles.introText}>
          <h1>Ask the company documents</h1>
          <p className={styles.muted}>
            Answers come only from the uploaded documents, with the file and page they came from. If the documents
            don&apos;t say, the assistant says it doesn&apos;t know.
          </p>
        </div>
        {/* three steps (numbers come from CSS; a list for screen readers) */}
        <ol className={styles.steps} aria-label="How to ask">
          <li>Pick a collection below</li>
          <li>Ask in plain words</li>
          <li>Open a source to check the page</li>
        </ol>
      </div>
      {collections.ok ? (
        <Composer
          collections={collections.data.map((c) => ({ name: c.name, documents: c.documents }))}
          historyCount={0}
          suggestions={suggestions}
        />
      ) : (
        <Problem message={displayMessage(collections.error)} />
      )}
    </section>
  );
}
