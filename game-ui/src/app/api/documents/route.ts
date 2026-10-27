import type { NextRequest } from "next/server";

import { apiUrl } from "@/lib/api/client";
import { clearSession, readSession } from "@/lib/session/cookie";

// POST /api/documents: the upload dialog's way to FastAPI's POST /v1/documents. The browser's multipart
// form (collection + file) is streamed straight through with the person's session pass added; nothing is
// buffered here. Kept out of proxy.ts's matcher: the proxy would buffer (and cut) bodies over 10 MB, and
// the session is checked right here anyway. Errors keep FastAPI's shape.

function fail(status: number, code: string, message: string): Response {
  return Response.json({ error: { code, message }, request_id: null }, { status });
}

export async function POST(request: NextRequest) {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (!origin || !host || URL.canParse(origin) === false || new URL(origin).host !== host) {
    return fail(403, "forbidden_origin", "Requests must come from the console itself.");
  }

  const session = await readSession();
  if (!session) {
    return fail(401, "invalid_session", "Your session has ended. Log in again.");
  }

  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.startsWith("multipart/form-data") || !request.body) {
    return fail(422, "invalid_request", "Choose a PDF and a collection.");
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${apiUrl()}/v1/documents`, {
      method: "POST",
      headers: { "Content-Type": contentType, "ITI-Console-Session": session },
      body: request.body,
      duplex: "half", // a streamed request body (Node's fetch requires saying so)
      cache: "no-store",
      signal: request.signal,
    } as RequestInit & { duplex: "half" });
  } catch {
    return fail(502, "api_unreachable", "The ITI AI service is not reachable. Check that FastAPI is running.");
  }

  if (upstream.status === 401) {
    await clearSession();
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
  });
}
