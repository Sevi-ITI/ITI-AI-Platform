import "server-only";

import { redirect } from "next/navigation";

import { currentAccount } from "./current-account";

// Testers have only the Chat page. Every other console page calls this first, so a tester who types its address
// lands on /chat. Each page checks for itself: a page always knows which page it is (a guard in the shared layout
// can't, on in-app navigations and server-action redirects). Cosmetic only: FastAPI refuses testers' admin calls.
export async function testersGoToChat(): Promise<void> {
  const me = await currentAccount();
  if (me.ok && me.data.role === "tester") redirect("/chat");
}
