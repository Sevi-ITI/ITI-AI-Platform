// 3D HQ or a plain list: the person's choice, in a cookie so the server renders the right one (no flash).
// Set by setView (app/(hq)/view-actions.ts). 3D is the default.

export const VIEW_COOKIE = "iti_game_view";

export type View = "3d" | "list";

export function viewFrom(value: string | undefined): View {
  return value === "list" ? "list" : "3d";
}
