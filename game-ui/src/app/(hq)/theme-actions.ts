"use server";

import { cookies } from "next/headers";

import { PHT_AUTO_COOKIE } from "@/hq/pht";
import { shownTheme, THEME_COOKIE } from "@/hq/theme";

// Flips dark/light and remembers it for a year. Next.js re-renders the page with the new data-theme.
// Copied from admin-ui/src/lib/theme-actions.ts. Flipping by hand also turns the PHT auto theme off (V2).
export async function toggleTheme(): Promise<void> {
  const store = await cookies();
  const next = shownTheme(store) === "dark" ? "light" : "dark";
  store.set(THEME_COOKIE, next, { path: "/", sameSite: "lax", httpOnly: true, maxAge: 60 * 60 * 24 * 365 });
  store.delete(PHT_AUTO_COOKIE);
}
