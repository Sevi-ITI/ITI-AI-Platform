"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { type ApiError, displayMessage } from "@/lib/api/api-error";
import type { components } from "@/lib/api/schema";

import { SendIcon, StopIcon } from "../icons";
import AddDocument from "./add-document";
import styles from "./chat.module.css";
import Message from "./message";
import { parseSse } from "./sse";

// The question box and the live answer. Posts to /api/chat (never to FastAPI), shows the answer while it
// is written, then lets the server re-render the saved conversation.

type Citation = components["schemas"]["Citation"];
type Turn = {
  question: string;
  answer: string;
  citations: Citation[] | null;
  state: "waiting" | "streaming" | "done" | "stopped" | "error";
  error?: ApiError;
  // The saved history had this many messages when the turn started; once the server shows more, the
  // saved copy replaces this live one.
  atCount: number;
};

export default function Composer({
  conversationId,
  fixedCollection,
  collections = [],
  historyCount,
}: {
  conversationId?: string;
  fixedCollection?: string; // an existing conversation keeps its collection
  collections?: { name: string; documents: number }[]; // a new chat picks one; the + dialog lists them
  historyCount: number;
}) {
  const router = useRouter();
  const [turn, setTurn] = useState<Turn | null>(null);
  const [collection, setCollection] = useState(
    fixedCollection ?? [...collections].sort((a, b) => b.documents - a.documents)[0]?.name ?? "",
  );
  const stopper = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);

  const busy = turn?.state === "waiting" || turn?.state === "streaming";

  // Open a conversation at its latest message, and follow the saved copy after each answer.
  // (on the next tick: when a link opens the page, Next.js first scrolls it to the top, which would undo this)
  // Runs again for another conversation even with the same message count (this component is reused).
  useEffect(() => {
    if (historyCount === 0) return;
    const timer = setTimeout(() =>
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "instant" }),
    );
    return () => clearTimeout(timer);
  }, [conversationId, historyCount]);
  const showTurn = turn !== null && turn.atCount === historyCount;

  async function send(question: string) {
    const controller = new AbortController();
    stopper.current = controller;
    const base = {
      question,
      answer: "",
      citations: null,
      atCount: historyCount,
    };
    setTurn({ ...base, state: "waiting" });
    requestAnimationFrame(() => end.current?.scrollIntoView({ behavior: "smooth", block: "end" }));

    let newId: string | null = null;
    let requestId: string | null = null;
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          collection,
          conversation_id: conversationId ?? null,
        }),
        signal: controller.signal,
      });
      if (res.redirected || res.status === 401) {
        router.push("/login"); // session over (the cookie is already cleared)
        return;
      }
      if (!res.ok || !res.body) {
        const body = await res.json().catch(() => null);
        setTurn({
          ...base,
          state: "error",
          error: errorFrom(res.status, body),
        });
        return;
      }

      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
      let buffer = "";
      let answer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        const parsed = parseSse(buffer + value);
        buffer = parsed.rest;
        for (const e of parsed.events) {
          const data = JSON.parse(e.data);
          if (e.event === "meta") {
            newId = data.conversation_id;
            requestId = data.request_id;
          }
          if (e.event === "token") {
            answer += data.text;
            setTurn({ ...base, answer, state: "streaming" });
          }
          // The final answer replaces what was streamed (it is cleaned up: sources list removed, [n] renumbered).
          if (e.event === "done")
            setTurn({
              ...base,
              answer: data.answer,
              citations: data.citations,
              state: "done",
            });
          if (e.event === "error") {
            // After the stream started the HTTP status is already 200: FastAPI's message is meant for people.
            setTurn({
              ...base,
              answer,
              state: "error",
              error: {
                status: 200,
                code: data.code,
                message: data.message,
                requestId,
              },
            });
          }
        }
      }
    } catch (err) {
      if (controller.signal.aborted) {
        setTurn((t) => (t ? { ...t, state: "stopped" } : t));
      } else {
        setTurn({ ...base, state: "error", error: errorFrom(0, null) });
        console.error("chat stream failed", err instanceof Error ? err.message : err);
      }
    } finally {
      stopper.current = null;
    }

    // Show the saved version: a new chat moves to its own page; an existing one re-renders its history.
    // refresh() also reloads the conversation list (the chat layout keeps its old copy on a page change).
    if (!conversationId && newId) router.push(`/chat/${newId}`);
    router.refresh();
  }

  function submit(form: HTMLFormElement) {
    const field = form.elements.namedItem("question") as HTMLTextAreaElement;
    const question = field.value.trim();
    if (!question || busy || !collection) return;
    field.value = "";
    void send(question);
  }

  return (
    <>
      {showTurn && (
        <>
          <Message role="user" content={turn.question} />
          {turn.state === "waiting" ? (
            <div className={styles.answer} aria-busy="true">
              <span className={styles.thinking}>Searching the documents and writing…</span>
            </div>
          ) : (
            turn.answer && (
              <div aria-busy={turn.state === "streaming"}>
                <Message role="assistant" content={turn.answer} citations={turn.citations} />
              </div>
            )
          )}
          {turn.state === "stopped" && <p className={styles.note}>Stopped. The answer above is incomplete.</p>}
          {turn.state === "error" && turn.error && (
            <div role="alert" className={styles.failed}>
              <p>
                ✕{" "}
                {turn.error.code === "llm_busy"
                  ? "The assistant is busy with other questions. Try again in a moment."
                  : turn.error.status === 200
                    ? turn.error.message
                    : displayMessage(turn.error)}
                {turn.error.requestId && (
                  <span className={styles.muted}>
                    {" "}
                    (request <span className="mono">{turn.error.requestId}</span>)
                  </span>
                )}
              </p>
              {(turn.error.code === "llm_busy" || turn.error.code === "llm_unavailable") && (
                <button type="button" className={styles.secondary} onClick={() => void send(turn.question)}>
                  Try again
                </button>
              )}
            </div>
          )}
        </>
      )}
      <p className="sr-only" aria-live="polite">
        {turn?.state === "done" ? "Answer ready." : turn?.state === "stopped" ? "Stopped." : ""}
      </p>
      <div ref={end} />

      {/* The + dialog has its own form, so it sits beside the question form, not inside it. */}
      <div className={styles.composer}>
        <div className={styles.box}>
          <AddDocument collections={collections.map((c) => c.name)} initial={collection} />
          <form
            className={styles.ask}
            onSubmit={(e) => {
              e.preventDefault();
              submit(e.currentTarget);
            }}
          >
            <textarea
              name="question"
              rows={1}
              maxLength={4000}
              placeholder={conversationId ? "Ask a follow-up…" : "Ask about the company documents…"}
              aria-label="Your question"
              onKeyDown={(e) => {
                // Enter sends, Shift+Enter makes a new line (not while an input method is composing text)
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  submit(e.currentTarget.form!);
                }
              }}
            />
            {busy ? (
              <button
                type="button"
                className={styles.round}
                onClick={() => stopper.current?.abort()}
                aria-label="Stop"
                title="Stop"
              >
                <StopIcon />
              </button>
            ) : (
              <button type="submit" className={styles.round} aria-label="Send" title="Send">
                <SendIcon />
              </button>
            )}
          </form>
        </div>
        <div className={styles.foot}>
          {!conversationId && (
            <select
              className={styles.chip}
              value={collection}
              onChange={(e) => setCollection(e.target.value)}
              disabled={busy}
              aria-label="Collection to ask"
            >
              {collections.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name} ({c.documents})
                </option>
              ))}
            </select>
          )}
          <p className={styles.hint}>Enter to send · Shift + Enter for a new line</p>
        </div>
      </div>
    </>
  );
}

function errorFrom(status: number, body: unknown): ApiError {
  const e =
    (body as {
      error?: { code?: string; message?: string };
      request_id?: string | null;
    } | null) ?? null;
  if (status === 0 || !e?.error) {
    return {
      status: status || 0,
      code: "unexpected",
      message: "The answer could not be loaded. Try again.",
      requestId: null,
    };
  }
  return {
    status,
    code: e.error.code ?? "unexpected",
    message: e.error.message ?? "Request failed.",
    requestId: e.request_id ?? null,
  };
}
