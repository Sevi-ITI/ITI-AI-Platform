// The person's theme choice, in a cookie so the server renders the right data-theme on <html> and the page never
// flashes the wrong theme. Set by toggleTheme (app/(hq)/theme-actions.ts). Dark is the default.
// Copied from admin-ui/src/lib/theme.ts; its own cookie name, so each console keeps its own choice.

export const THEME_COOKIE = "iti_game_theme";

export type Theme = "dark" | "light";

export function themeFrom(value: string | undefined): Theme {
  return value === "light" ? "light" : "dark";
}
