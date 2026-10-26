import { redirect } from "next/navigation";

import { clearSession } from "@/lib/session/cookie";

// Pages that get a 401 from FastAPI send the person here: a page can't delete a cookie while it renders,
// a route handler can. Then back to the login page.
export async function GET() {
  await clearSession();
  redirect("/login");
}
