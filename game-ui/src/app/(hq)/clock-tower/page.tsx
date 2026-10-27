import type { Metadata } from "next";
import { cookies } from "next/headers";

import { autoFrom, PHT_AUTO_COOKIE, PHT_SIM_COOKIE, simFrom } from "@/hq/pht";

import ClockPanel from "./clock-panel";

export const metadata: Metadata = { title: "PHT Clock Tower" };

// The clock tower room (V2): game-ui only, no FastAPI call. Super admins only: the shell shows a lock to anyone else
// (stations.ts canEnter). Its settings are cookies in this browser (pht.ts).
export default async function ClockTowerRoom() {
  const store = await cookies();
  return (
    <ClockPanel auto={autoFrom(store.get(PHT_AUTO_COOKIE)?.value)} sim={simFrom(store.get(PHT_SIM_COOKIE)?.value)} />
  );
}
