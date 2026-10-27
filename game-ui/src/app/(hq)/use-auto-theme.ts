"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { phtNow, themeForPht } from "@/hq/pht";
import type { Theme } from "@/hq/theme";

// While the PHT auto theme is on, look every 30 s whether Manila's time of day now wants the other theme; if so,
// ask the server for the page again (it decides the theme from the cookies, so there is one source of truth).
export function useAutoTheme(auto: boolean, sim: number | null, theme: Theme): void {
  const router = useRouter();
  useEffect(() => {
    if (!auto) return;
    const check = () => {
      if (themeForPht(phtNow(sim)) !== theme) router.refresh();
    };
    const timer = window.setInterval(check, 30_000);
    return () => window.clearInterval(timer);
  }, [auto, sim, theme, router]);
}
