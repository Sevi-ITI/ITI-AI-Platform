import "server-only";

import createClient, { type Client } from "openapi-fetch";

import { type ApiError, toApiError, unreachableError } from "@/lib/api/api-error";
import type { paths } from "@/lib/api/schema";
import { readSession } from "@/lib/session/cookie";

// The only way the console talks to FastAPI. Server-side only: the browser never calls FastAPI, and the
// console holds no API keys. Who is calling = the logged-in person's session pass, sent as a header.

export type ApiClient = Client<paths>;

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError };

function apiUrl(): string {
  const url = process.env.ITI_API_URL;
  if (!url) {
    throw new Error("ITI_API_URL is not set (see admin-ui/.env.example).");
  }
  return url;
}

/**
 * Calls FastAPI with the typed client and turns every outcome into one result:
 * `const me = await callApi((api) => api.GET("/v1/console/me"));`
 */
export async function callApi<T>(
  request: (api: ApiClient) => Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<ApiResult<T>> {
  const session = await readSession();
  const api = createClient<paths>({
    baseUrl: apiUrl(),
    headers: session ? { "ITI-Console-Session": session } : undefined,
    cache: "no-store",
  });

  let result: { data?: T; error?: unknown; response: Response };
  try {
    result = await request(api);
  } catch {
    // Network failure (FastAPI down). Nothing is logged: the request carried the session pass.
    return { ok: false, error: unreachableError() };
  }

  if (!result.response.ok) {
    return { ok: false, error: toApiError(result.response, result.error) };
  }
  return { ok: true, data: result.data as T };
}
