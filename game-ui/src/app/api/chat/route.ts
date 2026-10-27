import type { NextRequest } from "next/server";

import { apiUrl } from "@/lib/api/client";
import { clearSession, readSession } from "@/lib/session/cookie";

// POST /api/chat: the Chat page's only way to FastAPI. The browser sends the question here; this server
// code adds the person's session pass and passes FastAPI's answer stream (/v1/chat/stream, SSE) straight
// back. The pass never reaches the browser. Errors keep FastAPI's shape: {"error": {code, message}, request_id}.

function fail(status: number, code: string, message: string): Response {
  return Response.json({ error: { code, message }, request_id: null }, { status });
}

export async function POST(request: NextRequest) {
  // Only the console's own pages may post here (the Strict cookie already blocks other sites; this is a
  // second lock).
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (!origin || !host || URL.canParse(origin) === false || new URL(origin).host !== host) {
    return fail(403, "forbidden_origin", "Requests must come from the console itself.");
  }

  const session = await readSession();
  if (!session) {
    return fail(401, "invalid_session", "Your session has ended. Log in again.");
  }

  // Same limits as FastAPI's ChatRequest, so obvious mistakes never leave the console.
  const body = (await request.json().catch(() => null)) as Record<string, unknown> | null;
  const question = typeof body?.question === "string" ? body.question.trim() : "";
  const collection = typeof body?.collection === "string" ? body.collection : "";
  const conversationId = typeof body?.conversation_id === "string" ? body.conversation_id : null;
  if (!question || question.length > 4000 || !collection || collection.length > 64) {
    return fail(422, "invalid_request", "Type a question (up to 4,000 characters) and choose a collection.");
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${apiUrl()}/v1/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "ITI-Console-Session": session },
      body: JSON.stringify({ question, collection, conversation_id: conversationId }),
      cache: "no-store",
      // Stop button / closed tab: the browser aborts, and FastAPI is told to stop too.
      signal: request.signal,
    });
  } catch {
    return fail(502, "api_unreachable", "The ITI AI service is not reachable. Check that FastAPI is running.");
  }

  if (upstream.status === 401) {
    await clearSession();
  }
  if (!upstream.ok || !upstream.body) {
    // FastAPI's own error (busy, wrong collection, ...), passed on as it came.
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
    });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "X-Accel-Buffering": "no", // a future nginx in front must not hold the stream back
    },
  });
}
