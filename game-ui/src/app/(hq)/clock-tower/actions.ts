"use server";

import { cookies } from "next/headers";

import { PHT_AUTO_COOKIE, PHT_SIM_COOKIE } from "@/hq/pht";

// The clock tower's controls (V2). Both only change cookies in this browser; Next.js re-renders the page.

/** Turn the PHT auto theme on or off (remembered for a year). */
export async function setPhtAuto(on: boolean): Promise<void> {
  const store = await cookies();
  if (on) {
    store.set(PHT_AUTO_COOKIE, "on", { path: "/", sameSite: "lax", httpOnly: true, maxAge: 60 * 60 * 24 * 365 });
  } else {
    store.delete(PHT_AUTO_COOKIE);
  }
}

/** Simulate a time of day (minutes after midnight) until the browser closes; null = back to the live time. */
export async function setPhtSim(minutes: number | null): Promise<void> {
  const store = await cookies();
  if (minutes === null) {
    store.delete(PHT_SIM_COOKIE);
  } else if (Number.isInteger(minutes) && minutes >= 0 && minutes < 1440) {
    store.set(PHT_SIM_COOKIE, String(minutes), { path: "/", sameSite: "lax", httpOnly: true });
  }
}
