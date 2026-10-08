import "server-only";

import { cookies } from "next/headers";

// The person's FastAPI session pass (iti_cs_...) lives only in this httpOnly cookie: the browser's
// scripts can't read it, and it is never passed to client components or written to a log.

export const SESSION_COOKIE = "iti_console_session";

export async function readSession(): Promise<string | undefined> {
  return (await cookies()).get(SESSION_COOKIE)?.value;
}

/** Only in a server action or route handler (Next.js can't set cookies while a page renders). */
export async function saveSession(pass: string, expiresAt: string): Promise<void> {
  const secondsLeft = Math.floor((Date.parse(expiresAt) - Date.now()) / 1000);
  if (!Number.isFinite(secondsLeft) || secondsLeft <= 0) {
    throw new Error("The login returned an expiry time that is not in the future.");
  }

  (await cookies()).set(SESSION_COOKIE, pass, {
    httpOnly: true,
    sameSite: "strict",
    path: "/",
    maxAge: secondsLeft,
    secure: process.env.CONSOLE_COOKIE_SECURE === "true",
  });
}

/** Only in a server action or route handler. */
export async function clearSession(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
}
