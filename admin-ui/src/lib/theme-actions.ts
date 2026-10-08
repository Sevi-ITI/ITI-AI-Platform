"use server";

import { cookies } from "next/headers";

import { THEME_COOKIE, themeFrom } from "@/lib/theme";

// Flips dark/light and remembers it for a year. Next.js re-renders the page with the new data-theme.
export async function toggleTheme(): Promise<void> {
  const store = await cookies();
  const next = themeFrom(store.get(THEME_COOKIE)?.value) === "dark" ? "light" : "dark";
  store.set(THEME_COOKIE, next, { path: "/", sameSite: "lax", httpOnly: true, maxAge: 60 * 60 * 24 * 365 });
}
