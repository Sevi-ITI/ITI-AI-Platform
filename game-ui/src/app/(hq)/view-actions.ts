"use server";

import { cookies } from "next/headers";

import { VIEW_COOKIE, type View } from "@/hq/view";

// Switches between the 3D HQ and the list view and remembers it for a year. Next.js re-renders the layout.
export async function setView(view: View): Promise<void> {
  (await cookies()).set(VIEW_COOKIE, view, {
    path: "/",
    sameSite: "lax",
    httpOnly: true,
    maxAge: 60 * 60 * 24 * 365,
  });
}
