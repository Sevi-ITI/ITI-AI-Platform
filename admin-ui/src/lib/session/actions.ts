"use server";

import { redirect } from "next/navigation";

import { displayMessage } from "@/lib/api/api-error";
import { callApi } from "@/lib/api/client";
import { clearSession, saveSession } from "@/lib/session/cookie";

export type LoginState = { error: string | null; username: string };

// The password is only forwarded to FastAPI: never logged, never returned to the browser.
export async function logIn(_previous: LoginState, form: FormData): Promise<LoginState> {
  const username = String(form.get("username") ?? "").trim();
  const password = String(form.get("password") ?? "");

  const result = await callApi((api) => api.POST("/v1/console/login", { body: { username, password } }));
  if (!result.ok) {
    return { error: displayMessage(result.error), username };
  }

  await saveSession(result.data.session, result.data.expires_at);
  redirect("/");
}

export async function logOut(): Promise<void> {
  // A 401 here means the pass had already ended; the cookie is cleared either way.
  // ponytail: if FastAPI is unreachable the pass stays valid server-side until it expires (8 h).
  await callApi((api) => api.POST("/v1/console/logout"));
  await clearSession();
  redirect("/login");
}
