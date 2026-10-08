// The person's theme choice, in a cookie so the server renders the right data-theme on <html> and the
// page never flashes the wrong theme. Set by toggleTheme (theme-actions.ts). Dark is the default.

export const THEME_COOKIE = "iti_console_theme";

export type Theme = "dark" | "light";

export function themeFrom(value: string | undefined): Theme {
  return value === "light" ? "light" : "dark";
}
