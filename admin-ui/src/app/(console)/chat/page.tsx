import { displayMessage } from "@/lib/api/api-error";
import { endSessionOn401 } from "@/lib/api/client";

import { Problem } from "../widgets";
import styles from "./chat.module.css";
import Composer from "./composer";
import { chatCollections } from "./data";

export const metadata = { title: "Chat" };

// A new conversation: choose the collection (it stays fixed for the conversation), then ask.
export default async function NewChatPage() {
  const collections = await chatCollections();
  endSessionOn401(collections);

  return (
    <section className={styles.thread} aria-label="New chat">
      <div className={styles.empty}>
        <h1>Ask the company documents</h1>
        <p className={styles.muted}>
          Answers come only from the uploaded documents, with the file and page they came from. If the documents
          don&apos;t say, the assistant says it doesn&apos;t know.
        </p>
      </div>
      {collections.ok ? (
        <Composer
          collections={collections.data.map((c) => ({ name: c.name, documents: c.documents }))}
          historyCount={0}
        />
      ) : (
        <Problem message={displayMessage(collections.error)} />
      )}
    </section>
  );
}
