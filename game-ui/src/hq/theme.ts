// The person's theme choice, in a cookie so the server renders the right data-theme on <html> and the page never
// flashes the wrong theme. Set by toggleTheme (app/(hq)/theme-actions.ts). Dark is the default.
// Copied from admin-ui/src/lib/theme.ts; its own cookie name, so each console keeps its own choice.
// V2: with the PHT auto theme on (pht.ts), the time of day in Manila decides instead.

import { autoFrom, PHT_AUTO_COOKIE, PHT_SIM_COOKIE, phtNow, simFrom, themeForPht } from "@/hq/pht";

export const THEME_COOKIE = "iti_game_theme";

export type Theme = "dark" | "light";

export function themeFrom(value: string | undefined): Theme {
  return value === "light" ? "light" : "dark";
}

type CookieReader = { get(name: string): { value: string } | undefined };

/** The theme to show: the PHT one when the auto theme is on, else the person's choice. */
export function shownTheme(store: CookieReader): Theme {
  if (autoFrom(store.get(PHT_AUTO_COOKIE)?.value)) {
    return themeForPht(phtNow(simFrom(store.get(PHT_SIM_COOKIE)?.value)));
  }
  return themeFrom(store.get(THEME_COOKIE)?.value);
}
