import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { components } from "@/lib/api/schema";

import styles from "./chat.module.css";

// One chat bubble. Used by the server (history) and, in the next step, by the live answer in the browser,
// so it imports nothing server-only. Answers are Markdown; raw HTML in them is never rendered.

type Citation = components["schemas"]["Citation"];

export default function Message({
  role,
  content,
  citations,
}: {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[] | null;
}) {
  if (role === "user") {
    return <div className={styles.question}>{content}</div>;
  }
  return (
    <div className={styles.answer}>
      <div className={styles.markdown}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
      {citations && citations.length > 0 && <Sources citations={citations} />}
    </div>
  );
}

function Sources({ citations }: { citations: Citation[] }) {
  return (
    <div className={styles.sources}>
      <span className={styles.muted}>Sources</span>
      {citations.map((c, i) => (
        // Native <details>: click to see the start of the cited passage ("From p.N", not a quotation)
        <details key={`${c.doc_id}-${c.page}-${i}`} className={styles.source}>
          <summary>
            {i + 1}. {c.title.replace(/\.pdf$/i, "")}
            {c.page != null && <>, p.&nbsp;{c.page}</>}
          </summary>
          <p>
            <span className={styles.muted}>From p.&nbsp;{c.page ?? "?"}: </span>
            {c.snippet}…
          </p>
        </details>
      ))}
    </div>
  );
}
